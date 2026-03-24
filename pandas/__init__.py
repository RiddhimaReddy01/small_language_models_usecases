from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence


NA = None


def notna(value: Any) -> bool:
    return value is not None and not (isinstance(value, float) and math.isnan(value))


def _coerce_number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _mean(values: Sequence[Any]) -> float:
    nums = [_coerce_number(value) for value in values]
    valid = [value for value in nums if value is not None]
    return float(sum(valid) / len(valid)) if valid else 0.0


def _quantile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    index = p * (len(sorted_values) - 1)
    lower = int(math.floor(index))
    upper = int(math.ceil(index))
    if lower == upper:
        return sorted_values[lower]
    fraction = index - lower
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * fraction


class Series:
    def __init__(self, data: Iterable[Any] | None = None, index: list[int] | None = None, name: str | None = None, dtype: str | None = None):
        values = list(data or [])
        self._data = values
        self.index = list(index or range(len(values)))
        self.name = name
        self.dtype = dtype

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self) -> Iterator[Any]:
        return iter(self._data)

    def __getitem__(self, key: int) -> Any:
        return self._data[key]

    def __setitem__(self, key: int, value: Any) -> None:
        self._data[key] = value

    def __repr__(self) -> str:
        return f"Series({self._data!r})"

    @property
    def empty(self) -> bool:
        return len(self._data) == 0

    def copy(self) -> "Series":
        return Series(self._data.copy(), index=self.index.copy(), name=self.name, dtype=self.dtype)

    def to_list(self) -> list[Any]:
        return self._data.copy()

    def min(self) -> Any:
        values = [value for value in self._data if notna(value)]
        return min(values) if values else None

    def max(self) -> Any:
        values = [value for value in self._data if notna(value)]
        return max(values) if values else None

    def sum(self) -> Any:
        if all(isinstance(value, bool) for value in self._data if value is not None):
            return sum(1 for value in self._data if value)
        nums = [_coerce_number(value) for value in self._data]
        valid = [value for value in nums if value is not None]
        return sum(valid)

    def mean(self) -> float:
        return _mean(self._data)

    def fillna(self, value: Any) -> "Series":
        return Series([item if notna(item) else value for item in self._data], index=self.index.copy(), name=self.name, dtype=self.dtype)

    def astype(self, dtype: str | type) -> "Series":
        if dtype in ("Int64", int):
            converted = [None if value is None else int(value) for value in self._data]
        elif dtype in (bool, "bool"):
            converted = [bool(value) for value in self._data]
        elif dtype in (float, "float"):
            converted = [None if value is None else float(value) for value in self._data]
        else:
            converted = self._data.copy()
        return Series(converted, index=self.index.copy(), name=self.name, dtype=str(dtype))

    def dropna(self) -> "Series":
        values = [value for value in self._data if notna(value)]
        return Series(values, name=self.name, dtype=self.dtype)

    def notna(self) -> "Series":
        return Series([notna(value) for value in self._data], index=self.index.copy(), name=self.name)

    def all(self) -> bool:
        return all(bool(value) for value in self._data)

    def unique(self) -> list[Any]:
        unique_values: list[Any] = []
        for value in self._data:
            if value not in unique_values:
                unique_values.append(value)
        return unique_values

    def clip(self, lower: float | None = None, upper: float | None = None) -> "Series":
        clipped = []
        for value in self._data:
            number = _coerce_number(value)
            if number is None:
                clipped.append(value)
                continue
            if lower is not None:
                number = max(number, lower)
            if upper is not None:
                number = min(number, upper)
            clipped.append(number)
        return Series(clipped, index=self.index.copy(), name=self.name)

    def rolling(self, window: int, min_periods: int = 1, center: bool = False) -> "_RollingSeries":
        return _RollingSeries(self, window=window, min_periods=min_periods, center=center)

    def ewm(self, alpha: float, adjust: bool = False) -> "_EwmSeries":
        return _EwmSeries(self, alpha=alpha, adjust=adjust)

    def get(self, key: Any, default: Any = None) -> Any:
        try:
            return self._data[key]
        except (TypeError, IndexError):
            return default

    def __eq__(self, other: Any) -> "Series":
        if isinstance(other, Series):
            return Series([left == right for left, right in zip(self._data, other._data)], index=self.index.copy())
        return Series([value == other for value in self._data], index=self.index.copy())

    def __ne__(self, other: Any) -> "Series":
        if isinstance(other, Series):
            return Series([left != right for left, right in zip(self._data, other._data)], index=self.index.copy())
        return Series([value != other for value in self._data], index=self.index.copy())

    def __lt__(self, other: Any) -> "Series":
        if isinstance(other, Series):
            return Series([left < right for left, right in zip(self._data, other._data)], index=self.index.copy())
        return Series([value < other for value in self._data], index=self.index.copy())

    def __le__(self, other: Any) -> "Series":
        if isinstance(other, Series):
            return Series([left <= right for left, right in zip(self._data, other._data)], index=self.index.copy())
        return Series([value <= other for value in self._data], index=self.index.copy())

    def __gt__(self, other: Any) -> "Series":
        if isinstance(other, Series):
            return Series([left > right for left, right in zip(self._data, other._data)], index=self.index.copy())
        return Series([value > other for value in self._data], index=self.index.copy())

    def __ge__(self, other: Any) -> "Series":
        if isinstance(other, Series):
            return Series([left >= right for left, right in zip(self._data, other._data)], index=self.index.copy())
        return Series([value >= other for value in self._data], index=self.index.copy())

    def __and__(self, other: Any) -> "Series":
        other_series = other if isinstance(other, Series) else Series([other] * len(self))
        return Series([bool(left) and bool(right) for left, right in zip(self._data, other_series._data)], index=self.index.copy())

    def __or__(self, other: Any) -> "Series":
        other_series = other if isinstance(other, Series) else Series([other] * len(self))
        return Series([bool(left) or bool(right) for left, right in zip(self._data, other_series._data)], index=self.index.copy())

    def __truediv__(self, other: Any) -> "Series":
        if isinstance(other, Series):
            values = []
            for left, right in zip(self._data, other._data):
                left_num = _coerce_number(left)
                right_num = _coerce_number(right)
                values.append(0.0 if left_num is None or right_num in (None, 0.0) else left_num / right_num)
            return Series(values, index=self.index.copy())
        other_num = _coerce_number(other)
        values = [0.0 if _coerce_number(value) is None or other_num in (None, 0.0) else _coerce_number(value) / other_num for value in self._data]
        return Series(values, index=self.index.copy())


class _RollingSeries:
    def __init__(self, series: Series, window: int, min_periods: int, center: bool):
        self.series = series
        self.window = max(1, int(window))
        self.min_periods = min_periods
        self.center = center

    def mean(self) -> Series:
        values: list[Any] = []
        data = self.series.to_list()
        length = len(data)
        for index in range(length):
            if self.center:
                half = self.window // 2
                start = max(0, index - half)
                end = min(length, start + self.window)
            else:
                start = max(0, index - self.window + 1)
                end = index + 1
            window_values = [value for value in data[start:end] if notna(value)]
            if len(window_values) < self.min_periods:
                values.append(None)
            else:
                values.append(_mean(window_values))
        return Series(values, index=self.series.index.copy(), name=self.series.name)


class _EwmSeries:
    def __init__(self, series: Series, alpha: float, adjust: bool):
        self.series = series
        self.alpha = alpha
        self.adjust = adjust

    def mean(self) -> Series:
        values: list[Any] = []
        running: float | None = None
        for item in self.series:
            number = _coerce_number(item)
            if number is None:
                values.append(running)
                continue
            if running is None:
                running = number
            else:
                running = self.alpha * number + (1.0 - self.alpha) * running
            values.append(running)
        return Series(values, index=self.series.index.copy(), name=self.series.name)


class Row(dict):
    def to_dict(self) -> dict[str, Any]:
        return dict(self)


class _ILoc:
    def __init__(self, frame: "DataFrame"):
        self.frame = frame

    def __getitem__(self, key: int) -> Row:
        if key < 0:
            key += len(self.frame._rows)
        return Row(self.frame._rows[key].copy())


class DataFrame:
    def __init__(self, data: Iterable[Mapping[str, Any]] | Mapping[str, Sequence[Any]] | None = None, columns: Sequence[str] | None = None):
        rows: list[dict[str, Any]]
        if data is None:
            rows = []
        elif isinstance(data, Mapping):
            keys = list(columns or data.keys())
            length = max((len(data[key]) for key in keys), default=0)
            rows = []
            for index in range(length):
                row = {}
                for key in keys:
                    values = list(data[key])
                    row[key] = values[index] if index < len(values) else None
                rows.append(row)
        else:
            rows = [dict(row) for row in data]
        self._rows = rows
        ordered_columns: list[str] = []
        if columns:
            ordered_columns.extend(columns)
        for row in rows:
            for key in row.keys():
                if key not in ordered_columns:
                    ordered_columns.append(key)
        self._columns = ordered_columns
        self.iloc = _ILoc(self)

    def __len__(self) -> int:
        return len(self._rows)

    def __iter__(self) -> Iterator[str]:
        return iter(self._columns)

    def __contains__(self, key: str) -> bool:
        return key in self._columns

    def __getitem__(self, key: str | list[str] | Series) -> Any:
        if isinstance(key, str):
            return Series([row.get(key) for row in self._rows], index=list(range(len(self._rows))), name=key)
        if isinstance(key, Series):
            filtered = [row.copy() for row, include in zip(self._rows, key.to_list()) if include]
            return DataFrame(filtered, columns=self._columns.copy())
        filtered_rows = [{column: row.get(column) for column in key} for row in self._rows]
        return DataFrame(filtered_rows, columns=list(key))

    def __setitem__(self, key: str, value: Any) -> None:
        if isinstance(value, Series):
            values = value.to_list()
        elif isinstance(value, list):
            values = value
        else:
            values = [value] * len(self._rows)
        for index, row in enumerate(self._rows):
            row[key] = values[index] if index < len(values) else None
        if key not in self._columns:
            self._columns.append(key)

    @property
    def columns(self) -> list[str]:
        return self._columns.copy()

    @property
    def empty(self) -> bool:
        return len(self._rows) == 0

    def copy(self) -> "DataFrame":
        return DataFrame([row.copy() for row in self._rows], columns=self._columns.copy())

    def get(self, key: str, default: Any = None) -> Any:
        if key in self._columns:
            return self[key]
        return default

    def dropna(self, subset: Sequence[str] | None = None) -> "DataFrame":
        subset = list(subset or self._columns)
        rows = [row.copy() for row in self._rows if all(notna(row.get(column)) for column in subset)]
        return DataFrame(rows, columns=self._columns.copy())

    def rename(self, columns: Mapping[str, str]) -> "DataFrame":
        rows = []
        for row in self._rows:
            renamed = {}
            for key, value in row.items():
                renamed[columns.get(key, key)] = value
            rows.append(renamed)
        new_columns = [columns.get(column, column) for column in self._columns]
        return DataFrame(rows, columns=new_columns)

    def drop_duplicates(self, subset: Sequence[str] | None = None) -> "DataFrame":
        subset = list(subset or self._columns)
        seen = set()
        rows = []
        for row in self._rows:
            marker = tuple(row.get(column) for column in subset)
            if marker in seen:
                continue
            seen.add(marker)
            rows.append(row.copy())
        return DataFrame(rows, columns=self._columns.copy())

    def reset_index(self) -> "DataFrame":
        return self.copy()

    def sort_values(self, by: str) -> "DataFrame":
        rows = sorted(self._rows, key=lambda row: row.get(by))
        return DataFrame([row.copy() for row in rows], columns=self._columns.copy())

    def apply(self, func, axis: int = 0) -> "DataFrame" | Series:
        if axis != 1:
            raise NotImplementedError("Only axis=1 is supported")
        rows = []
        for row in self._rows:
            result = func(Row(row.copy()))
            rows.append(dict(result))
        return DataFrame(rows)

    def iterrows(self) -> Iterator[tuple[int, Row]]:
        for index, row in enumerate(self._rows):
            yield index, Row(row.copy())

    def groupby(self, by: str, sort: bool = True) -> "_GroupBy":
        return _GroupBy(self, by=by, sort=sort)

    def to_dict(self, orient: str = "records") -> list[dict[str, Any]]:
        if orient != "records":
            raise NotImplementedError("Only orient='records' is supported")
        return [row.copy() for row in self._rows]

    def to_csv(self, path: str | Path, index: bool = False) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=self._columns)
            writer.writeheader()
            for row in self._rows:
                writer.writerow({column: row.get(column) for column in self._columns})


class _GroupBy:
    def __init__(self, frame: DataFrame, by: str, sort: bool):
        self.frame = frame
        self.by = by
        self.sort = sort

    def agg(self, **aggregations: tuple[str, str]) -> DataFrame:
        grouped: dict[Any, list[dict[str, Any]]] = {}
        for row in self.frame._rows:
            grouped.setdefault(row.get(self.by), []).append(row)
        keys = sorted(grouped) if self.sort else list(grouped.keys())
        rows = []
        for key in keys:
            bucket = grouped[key]
            row = {self.by: key}
            for output_name, spec in aggregations.items():
                source, op = spec
                values = [item.get(source) for item in bucket]
                if op == "mean":
                    row[output_name] = _mean(values)
                elif op == "sum":
                    row[output_name] = sum(value for value in values if notna(value))
                else:
                    raise NotImplementedError(f"Unsupported aggregation: {op}")
            rows.append(row)
        return DataFrame(rows)


def DataFrame_from_records(records: Iterable[Mapping[str, Any]]) -> DataFrame:
    return DataFrame(records)


def merge(left: DataFrame, right: DataFrame, on: Sequence[str], how: str = "inner", suffixes: tuple[str, str] = ("_x", "_y")) -> DataFrame:
    if how != "inner":
        raise NotImplementedError("Only inner merge is supported")
    join_cols = list(on)
    right_index: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for row in right.to_dict():
        key = tuple(row.get(column) for column in join_cols)
        right_index.setdefault(key, []).append(row)
    rows = []
    for left_row in left.to_dict():
        key = tuple(left_row.get(column) for column in join_cols)
        for right_row in right_index.get(key, []):
            merged_row = left_row.copy()
            for column, value in right_row.items():
                if column in join_cols:
                    continue
                if column in merged_row:
                    merged_row[f"{column}{suffixes[1]}"] = value
                else:
                    merged_row[column] = value
            rows.append(merged_row)
    return DataFrame(rows)


def qcut(values: Series, q: int, labels: bool | Sequence[Any] = False, duplicates: str = "drop") -> Series:
    data = values.to_list()
    numeric = [float(value) for value in data if notna(value)]
    if not numeric:
        return Series([None] * len(data), index=values.index.copy())
    sorted_values = sorted(numeric)
    thresholds = [_quantile(sorted_values, step / q) for step in range(1, q)]
    bucketed = []
    for value in data:
        if notna(value):
            bucket = 0
            for threshold in thresholds:
                if float(value) > threshold:
                    bucket += 1
            bucketed.append(bucket)
        else:
            bucketed.append(None)
    return Series(bucketed, index=values.index.copy())


def cut(values: Series, bins: int, labels: bool | Sequence[Any] = False, include_lowest: bool = True) -> Series:
    data = values.to_list()
    numeric = [float(value) for value in data if notna(value)]
    if not numeric:
        return Series([None] * len(data), index=values.index.copy())
    minimum = min(numeric)
    maximum = max(numeric)
    if minimum == maximum:
        return Series([0 if notna(value) else None for value in data], index=values.index.copy())
    width = (maximum - minimum) / bins
    bucketed = []
    for value in data:
        if notna(value):
            if float(value) == maximum:
                bucketed.append(bins - 1)
            else:
                bucketed.append(int((float(value) - minimum) / width))
        else:
            bucketed.append(None)
    return Series(bucketed, index=values.index.copy())


def concat(parts: Sequence[DataFrame], ignore_index: bool = False) -> DataFrame:
    rows: list[dict[str, Any]] = []
    columns: list[str] = []
    for frame in parts:
        rows.extend(frame.to_dict())
        for column in frame.columns:
            if column not in columns:
                columns.append(column)
    return DataFrame(rows, columns=columns)


def read_csv(path: str | Path) -> DataFrame:
    source = Path(path)
    with source.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for row in reader:
            parsed = {}
            for key, value in row.items():
                if value is None or value == "":
                    parsed[key] = None if value == "" else value
                    continue
                try:
                    number = float(value)
                    parsed[key] = int(number) if number.is_integer() else number
                except ValueError:
                    if value.lower() == "true":
                        parsed[key] = True
                    elif value.lower() == "false":
                        parsed[key] = False
                    else:
                        try:
                            parsed[key] = json.loads(value)
                        except json.JSONDecodeError:
                            parsed[key] = value
            rows.append(parsed)
    return DataFrame(rows)


def read_json(path: str | Path, lines: bool = False) -> DataFrame:
    source = Path(path)
    if lines:
        rows = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
        return DataFrame(rows)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return DataFrame(payload)
    return DataFrame([payload])


class _ApiTypes:
    @staticmethod
    def is_numeric_dtype(series: Series) -> bool:
        return all(_coerce_number(value) is not None for value in series.to_list() if notna(value))


@dataclass
class _Api:
    types: _ApiTypes = _ApiTypes()


api = _Api()

