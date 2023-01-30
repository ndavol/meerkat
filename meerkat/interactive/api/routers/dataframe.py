from typing import Any, Dict, List, Union, Optional

import numpy as np
from fastapi import HTTPException
from pydantic import BaseModel, StrictInt, StrictStr

from meerkat.columns.scalar import ScalarColumn
from meerkat.columns.tensor.numpy import NumPyTensorColumn
from meerkat.dataframe import DataFrame
from meerkat.interactive.edit import EditTargetConfig
from meerkat.interactive.endpoint import Endpoint, endpoint
from meerkat.interactive.graph import trigger
from meerkat.interactive.modification import DataFrameModification
from meerkat.state import state


class ColumnInfo(BaseModel):
    name: str
    type: str
    cell_component: str
    cell_props: Dict[str, Any]
    cell_data_prop: str


class SchemaResponse(BaseModel):
    id: str
    columns: List[ColumnInfo]
    nrows: int = None
    primary_key: str = None


@endpoint(prefix="/df", route="/{df}/schema/")
def schema(
    df: DataFrame, columns: List[str]=None, variants: List[str]=None
) -> SchemaResponse:
    columns = df.columns if columns is None else columns
    return SchemaResponse(
        id=df.id,
        columns=_get_column_infos(df, columns, variants=variants),
        nrows=len(df),
        primary_key=df.primary_key_name,
    )


def _get_column_infos(
    df: DataFrame, columns: List[str] = None, variants: List[str] = None
):

    if columns is None:
        columns = df.columns
    else:
        missing_columns = set(columns) - set(df.columns)
        if len(missing_columns) > 0:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Requested columns {columns} do not exist in dataframe"
                    f" with id {df.id}"
                ),
            )

    columns = [column for column in columns if not column.startswith("_")]
    if df.primary_key_name is not None and df.primary_key_name not in columns:
        columns += [df.primary_key_name]
    return [
        ColumnInfo(
            name=col,
            type=type(df[col]).__name__,
            cell_component=df[col].formatter.component_class.alias,
            cell_props=df[col].formatter.get_props(variants=variants),
            cell_data_prop=df[col].formatter.data_prop,
        )
        for col in columns
    ]


class RowsResponse(BaseModel):
    column_infos: List[ColumnInfo]
    posidxs: List[int] = None
    rows: List[List[Any]]
    full_length: int
    # primary key
    primary_key: Optional[str] = None


@endpoint(prefix="/df", route="/{df}/rows/")
def rows(
    df: DataFrame,
    start: int = Endpoint.EmbeddedBody(None),
    end: int = Endpoint.EmbeddedBody(None),
    posidxs: List[int] = Endpoint.EmbeddedBody(None),
    key_column: str = Endpoint.EmbeddedBody(None),
    keyidxs: List[Union[StrictInt, StrictStr]] = Endpoint.EmbeddedBody(None),
    columns: List[str] = Endpoint.EmbeddedBody(None),
    variants: List[str] = Endpoint.EmbeddedBody(None),
) -> RowsResponse:
    """Get rows from a DataFrame as a JSON object."""

    full_length = len(df)
    column_infos = _get_column_infos(df, columns, variants=variants)

    df = df[[info.name for info in column_infos]]

    if posidxs is not None:
        df = df[posidxs]
        posidxs = posidxs
    elif start is not None:
        if end is None:
            end = len(df)
        else:
            end = min(end, len(df))
        df = df[start:end]
        posidxs = list(range(start, end))
    elif keyidxs is not None:
        if key_column is None:
            if df.primary_key is None:
                raise ValueError(
                    "Must provide key_column if keyidxs are provided and no "
                    "primary_key on dataframe."
                )
            df = df.loc[keyidxs]
        else:
            # FIXME(sabri): this will only work if key_column is a pandas column
            df = df[df[key_column].isin(keyidxs)]
    else:
        raise ValueError()

    rows = []
    for row in df:
        rows.append(
            [
                df[info.name].formatter.encode(row[info.name], variants=variants)
                for info in column_infos
            ]
        )
    return RowsResponse(
        column_infos=column_infos,
        rows=rows,
        full_length=full_length,
        posidxs=posidxs,
        primary_key=df.primary_key_name,
    )


@endpoint(prefix="/df", route="/{df}/remove_row_by_index/")
def remove_row_by_index(df: DataFrame, row_index: int = Endpoint.EmbeddedBody()):
    df = df[np.arange(len(df)) != row_index]

    # TODO: shouldn't have to issue this manually
    from meerkat.state import state

    state.modification_queue.add(
        DataFrameModification(id=df.inode.id, scope=df.columns)
    )


@endpoint(prefix="/df", route="/{df}/edit/")
def edit(
    df: DataFrame,
    value=Endpoint.EmbeddedBody(),  # don't set type
    column: str = Endpoint.EmbeddedBody(),
    row_id=Endpoint.EmbeddedBody(),
    id_column: str = Endpoint.EmbeddedBody(),
):
    mask = df[id_column] == row_id
    if mask.sum() == 0:
        raise HTTPException(f"Row with id {row_id} not found in column {id_column}")
    df[column][mask] = value

    # TODO: shouldn't have to issue this manually
    from meerkat.state import state

    state.modification_queue.add(DataFrameModification(id=df.inode.id, scope=[column]))


# @endpoint(prefix="/df", route="/{df}/edit_target/")
# def edit_target(
#     df: DataFrame,
#     target: EditTargetConfig = Endpoint.EmbeddedBody(),
#     value=Endpoint.EmbeddedBody(),  # don't set type
#     column: str = Endpoint.EmbeddedBody(),
#     row_indices: List[int] = Endpoint.EmbeddedBody(None),
#     row_keys: List[Union[StrictInt, StrictStr]] = Endpoint.EmbeddedBody(None),
#     primary_key: str = Endpoint.EmbeddedBody(None),
#     metadata: Dict[str, Any] = Endpoint.EmbeddedBody(None),
# ):
#     """Edit a target dataframe.

#     Args:
#         metadata (optional): Additional metadata to write.
#             This should be a mapping from column_name -> value.
#             Currently only unitary values are supported.
#     """
#     if (row_indices is None) == (row_keys is None):
#         raise HTTPException(
#             status_code=400,
#             detail="Exactly one of row_indices or row_keys must be specified",
#         )
#     # FIXME: this line won't work anymore!
#     print(target.target)
#     target_df = state.identifiables.get(group="refs", id=target.target.ref_id).obj

#     if row_indices is not None:
#         source_ids = df[target.source_id_column][row_indices]
#     else:
#         if primary_key is None:
#             # TODO(): make this work once we've implemented primary_key
#             raise NotImplementedError()
#             # primary_key = target_df.primary_key
#         source_ids = df[target.source_id_column][np.isin(df[primary_key], row_keys)]

#     mask = np.isin(target_df[target.target_id_column], source_ids)

#     if mask.sum() != (len(row_keys) if row_keys is not None else len(row_indices)):
#         raise HTTPException(
#             status_code=500, detail="Target dataframe does not contain all source ids."
#         )
#     target_df[column][mask] = value

#     # TODO: support making a column if the column does not exist.
#     # This requires deducing the column type and the default value
#     # to fill in.
#     if metadata is not None:
#         for column_name, col_value in metadata.items():
#             value = col_value
#             default = None
#             if isinstance(value, dict):
#                 value = col_value["value"]
#                 default = col_value["default"]
#             if column_name not in target_df.columns:
#                 if default is None:
#                     raise HTTPException(
#                         status_code=400,
#                         detail=f"Column {column_name} \
#                             does not exist in target dataframe",
#                     )
#                 default_col = np.full(len(target_df), default)
#                 if isinstance(default, str):
#                     default_col = ScalarColumn([default] * len(target_df))
#                 else:
#                     default_col = NumPyTensorColumn(np.full(len(target_df), default))
#                 target_df[column_name] = default_col
#             target_df[column_name][mask] = value

#     modifications = trigger(
#         # FIXME: this is not correct
#         modifications=[DataFrameModification(id=target.target.ref_id, scope=[column])]
#     )
#     return modifications
