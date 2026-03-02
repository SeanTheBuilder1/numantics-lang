from semantic_types import BuiltInTypes, ModifierClass, ModifierTypes


num_types = [
    BuiltInTypes.FLOAT_TYPE,
    BuiltInTypes.INT_TYPE,
    BuiltInTypes.CHAR_TYPE,
    BuiltInTypes.BOOL_TYPE,
]
int_types = [
    BuiltInTypes.INT_TYPE,
    BuiltInTypes.CHAR_TYPE,
    BuiltInTypes.BOOL_TYPE,
]

percent_types = [ModifierTypes.PERCENT_TYPE, ModifierTypes.XPERCENT_TYPE]
sign_types = [ModifierTypes.POSITIVE_TYPE, ModifierTypes.NEGATIVE_TYPE]
nonzero_types = [ModifierTypes.NONZERO_TYPE]
parity_types = [ModifierTypes.EVEN_TYPE, ModifierTypes.ODD_TYPE]
auto_type = [ModifierTypes.AUTO_TYPE]
time_types = [
    ModifierTypes.SECOND_TYPE,
    ModifierTypes.MINUTE_TYPE,
    ModifierTypes.HOUR_TYPE,
    ModifierTypes.DAY_TYPE,
    ModifierTypes.WEEK_TYPE,
    ModifierTypes.MONTH_TYPE,
    ModifierTypes.YEAR_TYPE,
]
distance_types = [
    ModifierTypes.METER_TYPE,
    ModifierTypes.MM_TYPE,
    ModifierTypes.CM_TYPE,
    ModifierTypes.KM_TYPE,
    ModifierTypes.FT_TYPE,
    ModifierTypes.INCH_TYPE,
]
area_types = [
    ModifierTypes.METER2_TYPE,
    ModifierTypes.MM2_TYPE,
    ModifierTypes.CM2_TYPE,
    ModifierTypes.KM2_TYPE,
    ModifierTypes.FT2_TYPE,
    ModifierTypes.INCH2_TYPE,
]
volume_types = [
    ModifierTypes.KL_TYPE,
    ModifierTypes.LITER_TYPE,
    ModifierTypes.ML_TYPE,
    ModifierTypes.CL_TYPE,
]
mass_types = [
    ModifierTypes.KG_TYPE,
    ModifierTypes.GRAM_TYPE,
    ModifierTypes.MG_TYPE,
    ModifierTypes.CG_TYPE,
]
temp_types = [
    ModifierTypes.KELV_TYPE,
    ModifierTypes.CELC_TYPE,
    ModifierTypes.FAHR_TYPE,
]
force_types = [
    ModifierTypes.NEWT_TYPE,
    ModifierTypes.KGF_TYPE,
    ModifierTypes.LBF_TYPE,
]
velocity_types = [
    ModifierTypes.MPS_TYPE,
    ModifierTypes.FPS_TYPE,
]
accel_types = [ModifierTypes.MPS2_TYPE]

exclusive_class = [
    ModifierClass.PERCENT,
    ModifierClass.TIME,
    ModifierClass.DISTANCE,
    ModifierClass.AREA,
    ModifierClass.VOLUME,
    ModifierClass.MASS,
    ModifierClass.TEMP,
    ModifierClass.FORCE,
    ModifierClass.VELOCITY,
    ModifierClass.ACCELERATION,
]

modifier_priority_table = {
    ModifierClass.PERCENT: percent_types,
    ModifierClass.TIME: time_types,
    ModifierClass.DISTANCE: distance_types,
    ModifierClass.AREA: area_types,
    ModifierClass.VOLUME: volume_types,
    ModifierClass.MASS: mass_types,
    ModifierClass.TEMP: temp_types,
    ModifierClass.FORCE: force_types,
    ModifierClass.VELOCITY: velocity_types,
    ModifierClass.ACCELERATION: accel_types,
}

multiple_based_units = [
    ModifierTypes.PERCENT_TYPE,
    ModifierTypes.XPERCENT_TYPE,
    ModifierTypes.POSITIVE_TYPE,
    ModifierTypes.NEGATIVE_TYPE,
    ModifierTypes.NONZERO_TYPE,
    ModifierTypes.EVEN_TYPE,
    ModifierTypes.ODD_TYPE,
    ModifierTypes.AUTO_TYPE,
    ModifierTypes.SECOND_TYPE,
    ModifierTypes.MINUTE_TYPE,
    ModifierTypes.HOUR_TYPE,
    ModifierTypes.DAY_TYPE,
    ModifierTypes.WEEK_TYPE,
    ModifierTypes.MONTH_TYPE,
    ModifierTypes.YEAR_TYPE,
    ModifierTypes.METER_TYPE,
    ModifierTypes.MM_TYPE,
    ModifierTypes.CM_TYPE,
    ModifierTypes.KM_TYPE,
    ModifierTypes.FT_TYPE,
    ModifierTypes.INCH_TYPE,
    ModifierTypes.METER2_TYPE,
    ModifierTypes.MM2_TYPE,
    ModifierTypes.CM2_TYPE,
    ModifierTypes.KM2_TYPE,
    ModifierTypes.FT2_TYPE,
    ModifierTypes.INCH2_TYPE,
    ModifierTypes.LITER_TYPE,
    ModifierTypes.ML_TYPE,
    ModifierTypes.CL_TYPE,
    ModifierTypes.KL_TYPE,
    ModifierTypes.GRAM_TYPE,
    ModifierTypes.MG_TYPE,
    ModifierTypes.CG_TYPE,
    ModifierTypes.KG_TYPE,
    ModifierTypes.NEWT_TYPE,
    ModifierTypes.KGF_TYPE,
    ModifierTypes.LBF_TYPE,
    ModifierTypes.MPS_TYPE,
    ModifierTypes.FPS_TYPE,
    ModifierTypes.MPS2_TYPE,
]

area_to_distance = {
    ModifierTypes.METER2_TYPE: ModifierTypes.METER_TYPE,
    ModifierTypes.MM2_TYPE: ModifierTypes.MM_TYPE,
    ModifierTypes.CM2_TYPE: ModifierTypes.CM_TYPE,
    ModifierTypes.KM2_TYPE: ModifierTypes.KM_TYPE,
    ModifierTypes.FT2_TYPE: ModifierTypes.FT_TYPE,
    ModifierTypes.INCH2_TYPE: ModifierTypes.INCH_TYPE,
}

volume_to_distance_and_area = {
    ModifierTypes.KL_TYPE: (ModifierTypes.METER_TYPE, ModifierTypes.METER2_TYPE),
    ModifierTypes.LITER_TYPE: (ModifierTypes.CM_TYPE, ModifierTypes.CM2_TYPE),
    ModifierTypes.ML_TYPE: (ModifierTypes.CM_TYPE, ModifierTypes.CM2_TYPE),
    ModifierTypes.CL_TYPE: (ModifierTypes.CM_TYPE, ModifierTypes.CM2_TYPE),
}

distance_to_area_and_volume = {
    ModifierTypes.METER_TYPE: (ModifierTypes.METER2_TYPE, ModifierTypes.KL_TYPE),
    ModifierTypes.CM_TYPE: (ModifierTypes.CM2_TYPE, ModifierTypes.ML_TYPE),
}

area_to_distance_and_volume = {
    ModifierTypes.METER2_TYPE: (ModifierTypes.METER_TYPE, ModifierTypes.KL_TYPE),
    ModifierTypes.CM2_TYPE: (ModifierTypes.CM_TYPE, ModifierTypes.ML_TYPE),
}

distance_to_area = {
    ModifierTypes.METER_TYPE: ModifierTypes.METER2_TYPE,
    ModifierTypes.MM_TYPE: ModifierTypes.MM2_TYPE,
    ModifierTypes.CM_TYPE: ModifierTypes.CM2_TYPE,
    ModifierTypes.KM_TYPE: ModifierTypes.KM2_TYPE,
    ModifierTypes.FT_TYPE: ModifierTypes.FT2_TYPE,
    ModifierTypes.INCH_TYPE: ModifierTypes.INCH2_TYPE,
}

distance_or_area_to_volume = {
    ModifierTypes.METER_TYPE: ModifierTypes.KL_TYPE,
    ModifierTypes.MM_TYPE: ModifierTypes.ML_TYPE,
    ModifierTypes.CM_TYPE: ModifierTypes.ML_TYPE,
    ModifierTypes.KM_TYPE: ModifierTypes.KL_TYPE,
    ModifierTypes.FT_TYPE: ModifierTypes.KL_TYPE,
    ModifierTypes.INCH_TYPE: ModifierTypes.KL_TYPE,
    ModifierTypes.METER2_TYPE: ModifierTypes.KL_TYPE,
    ModifierTypes.MM2_TYPE: ModifierTypes.ML_TYPE,
    ModifierTypes.CM2_TYPE: ModifierTypes.ML_TYPE,
    ModifierTypes.KM2_TYPE: ModifierTypes.KL_TYPE,
    ModifierTypes.FT2_TYPE: ModifierTypes.KL_TYPE,
    ModifierTypes.INCH2_TYPE: ModifierTypes.KL_TYPE,
}

int_promotion_table = {
    BuiltInTypes.FLOAT_TYPE: {
        BuiltInTypes.FLOAT_TYPE,
        BuiltInTypes.INT_TYPE,
        BuiltInTypes.CHAR_TYPE,
        BuiltInTypes.BOOL_TYPE,
    },
    BuiltInTypes.INT_TYPE: {
        BuiltInTypes.INT_TYPE,
        BuiltInTypes.CHAR_TYPE,
        BuiltInTypes.BOOL_TYPE,
    },
    BuiltInTypes.CHAR_TYPE: {BuiltInTypes.CHAR_TYPE, BuiltInTypes.BOOL_TYPE},
    BuiltInTypes.BOOL_TYPE: {BuiltInTypes.BOOL_TYPE},
}

distance_to_velocity = {
    ModifierTypes.METER_TYPE: ModifierTypes.MPS_TYPE,
    ModifierTypes.MM_TYPE: ModifierTypes.MPS_TYPE,
    ModifierTypes.CM_TYPE: ModifierTypes.MPS_TYPE,
    ModifierTypes.KM_TYPE: ModifierTypes.MPS_TYPE,
    ModifierTypes.FT_TYPE: ModifierTypes.FPS_TYPE,
    ModifierTypes.INCH_TYPE: ModifierTypes.FPS_TYPE,
}
