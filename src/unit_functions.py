from semantic_types import (
    BuiltInTypes,
    ExclusiveUnit,
    ModifierTypes,
    Type,
)
from type_functions import getModifierClass
from unit_conversion_table import baked_multiple_conversion_table


def unitConversionResultsInFloat(dest_unit: Type, src_unit: Type) -> bool:
    assert src_unit.exclusive and dest_unit.exclusive
    is_float, _ = baked_multiple_conversion_table[
        (src_unit.exclusive.unit, dest_unit.exclusive.unit)
    ]

    return is_float


def createUnitOnlyType(unit: ModifierTypes) -> Type:
    modifier_class = list(getModifierClass([unit]))
    assert len(modifier_class) == 1
    return Type(
        builtin=BuiltInTypes.INT_TYPE,
        modifiers=[unit],
        exclusive=ExclusiveUnit(unit=unit, unit_class=modifier_class[0]),
    )
