from enum import Enum
from semantic_types import (
    BuiltInTypes,
    ModifierClass,
    ModifierTypes,
    Type,
)
from type_functions import getExclusiveClass, getModifierClass
from unit_tables import modifier_priority_table


def is_close(lhs: float, rhs: float, precision: int = 10) -> bool:
    return abs(rhs - lhs) < float(1.5 * 10 ** (-precision))


def unitConversionResultsInFloatGenerator(
    dest_unit: Type, src_unit: Type
) -> tuple[bool, float]:
    value = 1.0
    value = convertToSiUnitResultsInFloat(value, src_unit)
    value = convertSiUnitToUnitResultsInFloat(value, dest_unit)
    return not is_close(value, round(value), 15), value


def convertToSiUnitResultsInFloat(value: float, type: Type) -> float:
    modifier_class = getModifierClass(type.modifiers)
    exclusive_class = getExclusiveClass(modifier_class)
    if exclusive_class == ModifierClass.PERCENT:
        return value
    elif exclusive_class == ModifierClass.TIME:
        if ModifierTypes.SECOND_TYPE in type.modifiers:
            return value
        elif ModifierTypes.MINUTE_TYPE in type.modifiers:
            return value * 60.0
        elif ModifierTypes.HOUR_TYPE in type.modifiers:
            return value * 3600.0
        elif ModifierTypes.DAY_TYPE in type.modifiers:
            return value * 86400.0
        elif ModifierTypes.WEEK_TYPE in type.modifiers:
            return value * 604800.0
        elif ModifierTypes.MONTH_TYPE in type.modifiers:
            return value * 26298000.0
        elif ModifierTypes.YEAR_TYPE in type.modifiers:
            return value * 315576000.0
    elif exclusive_class == ModifierClass.DISTANCE:
        if ModifierTypes.METER_TYPE in type.modifiers:
            return value
        elif ModifierTypes.MM_TYPE in type.modifiers:
            return value * 0.001
        elif ModifierTypes.CM_TYPE in type.modifiers:
            return value * 0.01
        elif ModifierTypes.KM_TYPE in type.modifiers:
            return value * 1000.0
        elif ModifierTypes.FT_TYPE in type.modifiers:
            return value * 0.3048
        elif ModifierTypes.INCH_TYPE in type.modifiers:
            return value * 0.0254
    elif exclusive_class == ModifierClass.AREA:
        if ModifierTypes.METER2_TYPE in type.modifiers:
            return value
        elif ModifierTypes.MM2_TYPE in type.modifiers:
            return value * 0.000001
        elif ModifierTypes.CM2_TYPE in type.modifiers:
            return value * 0.0001
        elif ModifierTypes.KM2_TYPE in type.modifiers:
            return value * 1000000.0
        elif ModifierTypes.FT2_TYPE in type.modifiers:
            return value * 0.09290304
        elif ModifierTypes.INCH2_TYPE in type.modifiers:
            return value * 0.00064516
    elif exclusive_class == ModifierClass.VOLUME:
        if ModifierTypes.KL_TYPE in type.modifiers:
            return value
        elif ModifierTypes.LITER_TYPE in type.modifiers:
            return value * 0.001
        elif ModifierTypes.ML_TYPE in type.modifiers:
            return value * 0.000001
        elif ModifierTypes.CL_TYPE in type.modifiers:
            return value * 0.00001
    elif exclusive_class == ModifierClass.MASS:
        if ModifierTypes.KG_TYPE in type.modifiers:
            return value
        elif ModifierTypes.GRAM_TYPE in type.modifiers:
            return value * 0.001
        elif ModifierTypes.MG_TYPE in type.modifiers:
            return value * 0.000001
        elif ModifierTypes.CG_TYPE in type.modifiers:
            return value * 0.00001
    elif exclusive_class == ModifierClass.TEMP:
        if ModifierTypes.KELV_TYPE in type.modifiers:
            return value
        elif ModifierTypes.CELC_TYPE in type.modifiers:
            return value + 273.15
        elif ModifierTypes.FAHR_TYPE in type.modifiers:
            return (value + 459.67) * (5.0 / 9.0)
    elif exclusive_class == ModifierClass.FORCE:
        if ModifierTypes.NEWT_TYPE in type.modifiers:
            return value
        elif ModifierTypes.KGF_TYPE in type.modifiers:
            return value * 9.80665
        elif ModifierTypes.LBF_TYPE in type.modifiers:
            return value * 4.4482216152605
    elif exclusive_class == ModifierClass.VELOCITY:
        if ModifierTypes.MPS_TYPE in type.modifiers:
            return value
        elif ModifierTypes.FPS_TYPE in type.modifiers:
            return value * 0.3048
    elif exclusive_class == ModifierClass.ACCELERATION:
        if ModifierTypes.MPS2_TYPE in type.modifiers:
            return value
    assert False


def convertSiUnitToUnitResultsInFloat(value: float, type: Type) -> float:
    modifier_class = getModifierClass(type.modifiers)
    exclusive_class = getExclusiveClass(modifier_class)
    if exclusive_class == ModifierClass.PERCENT:
        return value
    elif exclusive_class == ModifierClass.TIME:
        if ModifierTypes.SECOND_TYPE in type.modifiers:
            return value
        elif ModifierTypes.MINUTE_TYPE in type.modifiers:
            return value / 60.0
        elif ModifierTypes.HOUR_TYPE in type.modifiers:
            return value / 3600.0
        elif ModifierTypes.DAY_TYPE in type.modifiers:
            return value / 86400.0
        elif ModifierTypes.WEEK_TYPE in type.modifiers:
            return value / 604800.0
        elif ModifierTypes.MONTH_TYPE in type.modifiers:
            return value / 26298000.0
        elif ModifierTypes.YEAR_TYPE in type.modifiers:
            return value / 315576000.0
    elif exclusive_class == ModifierClass.DISTANCE:
        if ModifierTypes.METER_TYPE in type.modifiers:
            return value
        elif ModifierTypes.MM_TYPE in type.modifiers:
            return value * 1000.0
        elif ModifierTypes.CM_TYPE in type.modifiers:
            return value * 100.0
        elif ModifierTypes.KM_TYPE in type.modifiers:
            return value * 0.001
        elif ModifierTypes.FT_TYPE in type.modifiers:
            return value / 0.3048
        elif ModifierTypes.INCH_TYPE in type.modifiers:
            return value / 0.0254
    elif exclusive_class == ModifierClass.AREA:
        if ModifierTypes.METER2_TYPE in type.modifiers:
            return value
        elif ModifierTypes.MM2_TYPE in type.modifiers:
            return value * 1000000.0
        elif ModifierTypes.CM2_TYPE in type.modifiers:
            return value * 10000.0
        elif ModifierTypes.KM2_TYPE in type.modifiers:
            return value * 0.000001
        elif ModifierTypes.FT2_TYPE in type.modifiers:
            return value / 0.09290304
        elif ModifierTypes.INCH2_TYPE in type.modifiers:
            return value / 0.00064516
    elif exclusive_class == ModifierClass.VOLUME:
        if ModifierTypes.KL_TYPE in type.modifiers:
            return value
        elif ModifierTypes.LITER_TYPE in type.modifiers:
            return value * 1000.0
        elif ModifierTypes.ML_TYPE in type.modifiers:
            return value * 1000000.0
        elif ModifierTypes.CL_TYPE in type.modifiers:
            return value * 100000.0
    elif exclusive_class == ModifierClass.MASS:
        if ModifierTypes.KG_TYPE in type.modifiers:
            return value
        elif ModifierTypes.GRAM_TYPE in type.modifiers:
            return value * 1000.0
        elif ModifierTypes.MG_TYPE in type.modifiers:
            return value * 1000000.0
        elif ModifierTypes.CG_TYPE in type.modifiers:
            return value * 100000.0
    elif exclusive_class == ModifierClass.TEMP:
        if ModifierTypes.KELV_TYPE in type.modifiers:
            return value
        elif ModifierTypes.CELC_TYPE in type.modifiers:
            return value - 273.15
        elif ModifierTypes.FAHR_TYPE in type.modifiers:
            return (value * (5.0 / 9.0)) - 459.67
    elif exclusive_class == ModifierClass.FORCE:
        if ModifierTypes.NEWT_TYPE in type.modifiers:
            return value
        elif ModifierTypes.KGF_TYPE in type.modifiers:
            return value / 9.80665
        elif ModifierTypes.LBF_TYPE in type.modifiers:
            return value / 4.4482216152605
    elif exclusive_class == ModifierClass.VELOCITY:
        if ModifierTypes.MPS_TYPE in type.modifiers:
            return value
        elif ModifierTypes.FPS_TYPE in type.modifiers:
            return value / 0.3048
    elif exclusive_class == ModifierClass.ACCELERATION:
        if ModifierTypes.MPS2_TYPE in type.modifiers:
            return value
    assert False


conversion_table = dict()
for modifier_class in modifier_priority_table.values():
    for type1 in modifier_class:
        for type2 in modifier_class:
            src_type = Type(builtin=BuiltInTypes.INT_TYPE, modifiers=[type1])
            dest_type = Type(builtin=BuiltInTypes.INT_TYPE, modifiers=[type2])
            conversion_table[(type1, type2)] = unitConversionResultsInFloatGenerator(
                dest_type, src_type
            )


def clean_repr(obj):
    if isinstance(obj, Enum):
        return f"{obj.__class__.__name__}.{obj.name}"
    elif isinstance(obj, str):
        return repr(obj)
    elif isinstance(obj, list):
        return "[" + ", ".join(clean_repr(x) for x in obj) + "]"
    elif isinstance(obj, tuple):
        return (
            "("
            + ", ".join(clean_repr(x) for x in obj)
            + ("," if len(obj) == 1 else "")
            + ")"
        )
    elif isinstance(obj, set):
        if not obj:
            return "set()"
        return "{" + ", ".join(clean_repr(x) for x in obj) + "}"
    elif isinstance(obj, dict):
        items = (f"{clean_repr(k)}: {clean_repr(v)}" for k, v in obj.items())
        return "{" + ", ".join(items) + "}"
    else:
        return repr(obj)


print(clean_repr(conversion_table))
