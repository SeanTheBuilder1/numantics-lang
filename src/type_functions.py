from semantic_types import BuiltInTypes, ModifierClass, ModifierTypes, Type
from unit_tables import (
    percent_types,
    sign_types,
    nonzero_types,
    parity_types,
    auto_type,
    time_types,
    distance_types,
    area_types,
    volume_types,
    mass_types,
    temp_types,
    force_types,
    velocity_types,
    accel_types,
    exclusive_class,
)


def isTypeCompatible(dest: Type, src: Type) -> bool:
    if len(src.modifiers) == 0 and len(dest.modifiers) == 0:
        if (
            dest.builtin == BuiltInTypes.FLOAT_TYPE
            and src.builtin == BuiltInTypes.INT_TYPE
        ):
            return True
        if dest.builtin == BuiltInTypes.BOOL_TYPE and src.builtin in [
            BuiltInTypes.INT_TYPE,
            BuiltInTypes.FLOAT_TYPE,
            BuiltInTypes.BOOL_TYPE,
            BuiltInTypes.CHAR_TYPE,
            BuiltInTypes.STRING_TYPE,
        ]:
            return True
        if (
            dest.builtin == BuiltInTypes.INT_TYPE
            and src.builtin == BuiltInTypes.CHAR_TYPE
        ):
            return True
    return False


def getModifierClass(modifiers: list[ModifierTypes]) -> set[ModifierClass]:
    modifier_classes = set()

    for modifier in modifiers:
        if modifier in percent_types:
            modifier_classes.add(ModifierClass.PERCENT)
        elif modifier in sign_types:
            modifier_classes.add(ModifierClass.SIGN)
        elif modifier in nonzero_types:
            modifier_classes.add(ModifierClass.NONZERO)
        elif modifier in parity_types:
            modifier_classes.add(ModifierClass.PARITY)
        elif modifier in time_types:
            modifier_classes.add(ModifierClass.TIME)
        elif modifier in distance_types:
            modifier_classes.add(ModifierClass.DISTANCE)
        elif modifier in area_types:
            modifier_classes.add(ModifierClass.AREA)
        elif modifier in volume_types:
            modifier_classes.add(ModifierClass.VOLUME)
        elif modifier in mass_types:
            modifier_classes.add(ModifierClass.MASS)
        elif modifier in temp_types:
            modifier_classes.add(ModifierClass.TEMP)
        elif modifier in force_types:
            modifier_classes.add(ModifierClass.FORCE)
        elif modifier in velocity_types:
            modifier_classes.add(ModifierClass.VELOCITY)
        elif modifier in accel_types:
            modifier_classes.add(ModifierClass.ACCELERATION)
        elif modifier in auto_type:
            return {ModifierClass.AUTO}
    return modifier_classes


def getExclusiveClass(
    modifier_classes: set[ModifierClass],
) -> ModifierClass | None:
    for modifier_class in modifier_classes:
        if modifier_class in exclusive_class:
            return modifier_class
