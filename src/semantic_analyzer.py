from __future__ import annotations
from semantic_types import (
    BuiltInTypes,
    Function,
    ModifierClass,
    ModifierTypes,
    Parameter,
    Scope,
    Symbol,
    Type,
)
from ast_types import ASTLiteral, ASTNode, ASTNodeType, ASTOperator, BinaryOpData
from collections import Counter
from enum import Enum, auto
from dataclasses import dataclass
import copy


class StatementInterruptType(Enum):
    LOOP = 1
    SWITCH = auto()
    FUNCTION = auto()


@dataclass
class StatementInterrupt:
    kind: StatementInterruptType
    node: ASTNode


def resolveFile(tree: ASTNode, code: str) -> tuple[Scope, bool]:
    scope = Scope()
    statement_stack: list[StatementInterrupt] = []
    has_error = False

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
        ModifierTypes.LITER_TYPE,
        ModifierTypes.ML_TYPE,
        ModifierTypes.CL_TYPE,
        ModifierTypes.KL_TYPE,
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

    area_to_distance = {
        ModifierTypes.METER2_TYPE: ModifierTypes.METER_TYPE,
        ModifierTypes.MM2_TYPE: ModifierTypes.MM_TYPE,
        ModifierTypes.CM2_TYPE: ModifierTypes.CM_TYPE,
        ModifierTypes.KM2_TYPE: ModifierTypes.KM_TYPE,
        ModifierTypes.FT2_TYPE: ModifierTypes.FT_TYPE,
        ModifierTypes.INCH2_TYPE: ModifierTypes.INCH_TYPE,
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

    def nonFatalError(*args):
        nonlocal has_error
        print(*args)
        has_error = True

    def define(scope: Scope, name: str, symbol: Symbol):
        if scope.symbols.get(name):
            nonFatalError(f"ERROR: redefinition of symbol '{name}'")
            return
        scope.symbols[name] = symbol

    def reference(scope: Scope, name: str, error_on_empty=False) -> Symbol | None:
        top_scope = scope
        while top_scope:
            result = top_scope.symbols.get(name)
            if result:
                return result
            top_scope = top_scope.parent_scope
        if error_on_empty:
            nonFatalError(f"ERROR: undefined symbol '{name}'")

        return None

    def resolveStatement(tree: ASTNode, scope: Scope):
        if tree.kind == ASTNodeType.DECLARATION:
            resolveDeclaration(tree, scope)
        elif tree.kind == ASTNodeType.IF_STMT:
            resolveIfStmt(tree, scope)
        elif tree.kind == ASTNodeType.SWITCH_STMT:
            resolveSwitchStmt(tree, scope)
        elif tree.kind == ASTNodeType.SWEEP_STMT:
            resolveSweepStmt(tree, scope)
        elif tree.kind == ASTNodeType.WHILE_STMT:
            resolveWhileStmt(tree, scope)
        elif tree.kind == ASTNodeType.FUNCTION_STMT:
            resolveFunctionStmt(tree, scope)
        elif tree.kind == ASTNodeType.FOR_STMT:
            resolveForStmt(tree, scope)
        elif tree.kind == ASTNodeType.BLOCK:
            resolveBlock(tree, scope)
        elif tree.kind == ASTNodeType.NEXT_STMT:
            resolveNextStmt(tree, scope)
        elif tree.kind == ASTNodeType.STOP_STMT:
            resolveStopStmt(tree, scope)
        elif tree.kind == ASTNodeType.RETURN_STMT:
            resolveReturnStmt(tree, scope)
        else:
            resolveExpression(tree, scope)

    def resolveIfStmt(tree: ASTNode, scope: Scope):
        resolveExpression(tree.data.expr, scope)
        resolveBlock(tree.data.block, scope)
        for expr, block in tree.data.elif_stmts:
            resolveExpression(expr, scope)
            resolveBlock(block, scope)
        if tree.data.else_stmt:
            resolveBlock(tree.data.else_stmt, scope)

    def resolveSwitchStmt(tree: ASTNode, scope: Scope):
        expr = resolveExpression(tree.data.expr, scope)
        statement_stack.append(
            StatementInterrupt(kind=StatementInterruptType.SWITCH, node=tree)
        )
        for case_expr, case_node in tree.data.case_stmts:
            resolveExpression(case_expr, scope)
            resolveStatement(case_node, scope)
        if tree.data.default_stmt:
            resolveStatement(tree.data.default_stmt, scope)
        statement_stack.pop()

    def resolveSweepStmt(tree: ASTNode, scope: Scope):
        expr = resolveExpression(tree.data.expr, scope)
        if expr.builtin not in [BuiltInTypes.FLOAT_TYPE, BuiltInTypes.INT_TYPE]:
            nonFatalError("ERROR: sweep statements only support numerical values")
        statement_stack.append(
            StatementInterrupt(kind=StatementInterruptType.SWITCH, node=tree)
        )
        for expr, node in tree.data.range_stmts:
            type = resolveExpression(expr, scope)
            if type.builtin not in [BuiltInTypes.FLOAT_TYPE, BuiltInTypes.INT_TYPE]:
                nonFatalError("ERROR: sweep statements only support numerical values")
            resolveStatement(node, scope)
        if tree.data.default_stmt:
            resolveStatement(tree.data.default_stmt, scope)
        statement_stack.pop()

    def resolveWhileStmt(tree: ASTNode, scope: Scope):
        resolveExpression(tree.data.left_expr, scope)
        if tree.data.right_expr:
            resolveExpression(tree.data.right_expr, scope)
        statement_stack.append(
            StatementInterrupt(kind=StatementInterruptType.LOOP, node=tree)
        )
        resolveBlock(tree.data.block, scope)
        statement_stack.pop()

    def resolveForStmt(tree: ASTNode, scope: Scope):
        tree.scope = Scope(parent_scope=scope)
        scope.children.append(tree.scope)
        if tree.data.init:
            if tree.data.init.kind == ASTNodeType.DECLARATION:
                resolveDeclaration(tree.data.init, tree.scope)
            else:
                resolveExpression(tree.data.init, tree.scope)
        if tree.data.condition:
            resolveExpression(tree.data.condition, tree.scope)
        if tree.data.update:
            resolveExpression(tree.data.update, tree.scope)
        statement_stack.append(
            StatementInterrupt(kind=StatementInterruptType.LOOP, node=tree)
        )
        resolveBlock(tree.data.block, tree.scope)
        statement_stack.pop()

    def resolveBlock(tree: ASTNode, scope: Scope):
        tree.scope = Scope(parent_scope=scope)
        scope.children.append(tree.scope)
        for node in tree.data.statements:
            resolveStatement(node, tree.scope)

    def resolveFunctionBlock(tree: ASTNode, scope: Scope):
        for node in tree.data.statements:
            resolveStatement(node, scope)

    def resolveNextStmt(tree: ASTNode, scope):
        for stmt in reversed(statement_stack):
            if stmt.kind == StatementInterruptType.LOOP:
                tree.data.target = stmt.node
                return
            elif stmt.kind == StatementInterruptType.FUNCTION:
                break
        nonFatalError("ERROR: next used outside loop")

    def resolveStopStmt(tree: ASTNode, scope):
        for stmt in reversed(statement_stack):
            if stmt.kind in [
                StatementInterruptType.LOOP,
                StatementInterruptType.SWITCH,
            ]:
                tree.data.target = stmt.node
                return
            elif stmt.kind == StatementInterruptType.FUNCTION:
                break
        nonFatalError("ERROR: stop used outside loop or switch")

    def resolveReturnStmt(tree: ASTNode, scope):
        expr = None
        if tree.data.expression:
            expr = resolveExpression(tree.data.expression, scope)
        for stmt in reversed(statement_stack):
            if stmt.kind == StatementInterruptType.FUNCTION:
                tree.data.target = stmt.node
                if (
                    stmt.node.data.return_type.builtin == BuiltInTypes.VOID_TYPE
                    and expr
                ):
                    nonFatalError(
                        f"ERROR: Invalid return type {expr} for function with no return type"
                    )
                if (
                    not expr
                    and stmt.node.data.return_type.builtin != BuiltInTypes.VOID_TYPE
                ):
                    nonFatalError(
                        f"ERROR: Missing return value of type {stmt.node.data.return_type}"
                    )
                if expr and not isTypeCastable(expr, stmt.node.data.return_type):
                    nonFatalError(
                        f"ERROR: Invalid return type {expr} for function with return type {stmt.node.data.return_type}"
                    )
                return
        nonFatalError("ERROR: Return used outside function body")

    def resolveFunctionStmt(tree: ASTNode, scope: Scope):
        tree.scope = Scope(parent_scope=scope)
        scope.children.append(tree.scope)
        func_name = resolveIdentifier(tree.data.name, scope)
        resolveType(tree.data.return_type, scope)
        params: list[Parameter] = []
        for type, name_node in tree.data.parameters:
            name = resolveIdentifier(name_node, scope)
            resolveType(type, scope)
            symbol = Symbol(name=name, type=type, scope=tree.scope)
            params.append(Parameter(type, name))
            define(tree.scope, name, symbol)
        symbol = Symbol(
            name=func_name,
            type=Function(return_type=tree.data.return_type, parameters=params),
            scope=scope,
        )
        define(scope, func_name, symbol)
        statement_stack.append(
            StatementInterrupt(kind=StatementInterruptType.FUNCTION, node=tree)
        )
        resolveFunctionBlock(tree.data.block, tree.scope)
        statement_stack.pop()

    def resolveDeclaration(tree: ASTNode, scope: Scope):
        resolveType(tree.data.type, scope)
        type = tree.data.type
        is_auto: bool = ModifierClass.AUTO in getModifierClass(tree.data.type.modifiers)
        name = resolveIdentifier(tree.data.name, scope)
        if type.builtin == BuiltInTypes.VOID_TYPE:
            nonFatalError(f"ERROR: named variable {name} cannot be void type")
        expr = None
        if tree.data.expression:
            expr = resolveExpression(tree.data.expression, scope)
        if not expr and is_auto:
            nonFatalError("ERROR: Auto type declaration must have a derived type")
        if expr:
            if is_auto:
                type.modifiers = expr.modifiers
                type.exclusive = expr.exclusive
                tree.data.type = type
            elif not isTypeCastable(tree.data.type, expr):
                nonFatalError(f"ERROR: Declared type {type} is not castable to {expr}")

        symbol = Symbol(name=name, type=type, scope=scope)
        tree.data.name.data.symbol = symbol
        define(scope, name, symbol)

    def resolveIdentifier(tree: ASTNode, scope: Scope):
        return code[tree.token.start : tree.token.end]

    def resolveExpression(tree: ASTNode, scope: Scope) -> Type:
        if tree.kind == ASTNodeType.BINARY_OP:
            return resolveBinaryOp(tree, scope)
        elif tree.kind == ASTNodeType.UNARY_OP:
            return resolveUnaryOp(tree, scope)
        elif tree.kind == ASTNodeType.FUNCTION_CALL:
            return resolveFunctionCall(tree, scope)
        elif tree.kind == ASTNodeType.ARRAY_INDEX:
            return resolveArrayIndex(tree, scope)
        elif tree.kind == ASTNodeType.LITERAL:
            return resolveLiteral(tree, scope)
        elif tree.kind == ASTNodeType.IDENTIFIER:
            symbol = resolveSymbol(tree, scope)
            if isinstance(symbol, Function):
                nonFatalError("ERROR: Sole function cannot be used in expression")
                return Type(builtin=BuiltInTypes.VOID_TYPE)
            else:
                tree.data.type = symbol
            return symbol
        assert False

    def resolveBinaryOp(tree: ASTNode, scope: Scope) -> Type:
        lhs = tree.data.lhs
        rhs = tree.data.rhs
        lhs_type = resolveExpression(lhs, scope)
        rhs_type = resolveExpression(rhs, scope)
        operator = tree.data.operator
        new_builtin: BuiltInTypes = BuiltInTypes.VOID_TYPE
        new_modifiers: list[ModifierTypes] = []

        if (
            lhs_type.builtin == BuiltInTypes.VOID_TYPE
            or rhs_type.builtin == BuiltInTypes.VOID_TYPE
        ):
            nonFatalError("ERROR: void type is invalid operand for binary operation")
            return Type(builtin=BuiltInTypes.VOID_TYPE)
        elif operator == ASTOperator.ADD_OPERATOR:
            if (
                lhs_type.builtin == BuiltInTypes.STRING_TYPE
                or rhs_type.builtin == BuiltInTypes.STRING_TYPE
            ):
                if lhs_type.builtin != BuiltInTypes.STRING_TYPE:
                    nonFatalError(
                        f"ERROR: Invalid lhs operand {lhs_type} must be string type"
                    )
                elif rhs_type.builtin != BuiltInTypes.STRING_TYPE:
                    nonFatalError(
                        f"ERROR: Invalid rhs operand {rhs_type} must be string type"
                    )
                else:
                    new_builtin = BuiltInTypes.STRING_TYPE
            elif lhs_type.builtin in num_types or rhs_type.builtin in num_types:
                for int_type in num_types:
                    if lhs_type.builtin == int_type or rhs_type.builtin == int_type:
                        if lhs_type.builtin not in int_promotion_table[int_type]:
                            nonFatalError(
                                f"ERROR: Invalid lhs operand {lhs_type} must be numerical type"
                            )
                        elif rhs_type.builtin not in int_promotion_table[int_type]:
                            nonFatalError(
                                f"ERROR: Invalid rhs operand {rhs_type} must be numerical type"
                            )
                        else:
                            new_builtin = int_type
                            break

            lhs_class = getModifierClass(lhs_type.modifiers)
            rhs_class = getModifierClass(rhs_type.modifiers)

            # EXCLUSIVE CLASS
            for modifier in modifier_priority_table.keys():
                if modifier not in lhs_class and modifier not in rhs_class:
                    continue
                if modifier not in lhs_class or modifier not in rhs_class:
                    nonFatalError(
                        f"ERROR: mismatched exclusive modifier types {lhs_type} and {rhs_type}"
                    )
                    break
                for type in modifier_priority_table[modifier]:
                    if type in lhs_type.modifiers or type in rhs_type.modifiers:
                        new_modifiers.append(type)
                        break

            # INCLUSIVE CLASS
            if ModifierClass.SIGN in lhs_class and ModifierClass.SIGN in rhs_class:
                if (
                    ModifierTypes.POSITIVE_TYPE in lhs_type.modifiers
                    and ModifierTypes.POSITIVE_TYPE in rhs_type.modifiers
                ):
                    new_modifiers.append(ModifierTypes.POSITIVE_TYPE)
                elif (
                    ModifierTypes.NEGATIVE_TYPE in lhs_type.modifiers
                    and ModifierTypes.NEGATIVE_TYPE in rhs_type.modifiers
                ):
                    new_modifiers.append(ModifierTypes.NEGATIVE_TYPE)
                else:
                    pass
            elif ModifierClass.SIGN in lhs_class:
                pass
            elif ModifierClass.SIGN in rhs_class:
                pass

            if (
                ModifierClass.NONZERO in lhs_class
                and ModifierClass.NONZERO in rhs_class
            ):
                pass
            elif ModifierClass.NONZERO in lhs_class:
                pass
            elif ModifierClass.NONZERO in rhs_class:
                pass

            if ModifierClass.PARITY in lhs_class and ModifierClass.PARITY in rhs_class:
                if (
                    ModifierTypes.EVEN_TYPE in lhs_type.modifiers
                    and ModifierTypes.EVEN_TYPE in rhs_type.modifiers
                ):
                    new_modifiers.append(ModifierTypes.EVEN_TYPE)
                else:
                    new_modifiers.append(ModifierTypes.ODD_TYPE)
            elif ModifierClass.PARITY in lhs_class:
                pass
            elif ModifierClass.PARITY in rhs_class:
                pass
            tree.data.type = type(builtin=new_builtin, modifiers=new_modifiers)
            return tree.data.type

        elif operator == ASTOperator.SUB_OPERATOR:
            if lhs_type.builtin in num_types or rhs_type.builtin in num_types:
                for int_type in num_types:
                    if lhs_type.builtin == int_type or rhs_type.builtin == int_type:
                        if lhs_type.builtin not in int_promotion_table[int_type]:
                            nonFatalError(
                                f"ERROR: Invalid lhs operand {lhs_type} must be numerical type"
                            )
                            break
                        elif rhs_type.builtin not in int_promotion_table[int_type]:
                            nonFatalError(
                                f"ERROR: Invalid rhs operand {rhs_type} must be numerical type"
                            )
                            break
                        else:
                            new_builtin = int_type
                            break
            else:
                nonFatalError(
                    f"ERROR: Invalid operands {lhs_type}, {rhs_type} for binary operation"
                )

            lhs_class = getModifierClass(lhs_type.modifiers)
            rhs_class = getModifierClass(rhs_type.modifiers)

            # EXCLUSIVE CLASS
            for modifier in modifier_priority_table.keys():
                if modifier not in lhs_class and modifier not in rhs_class:
                    continue
                if modifier not in lhs_class or modifier not in rhs_class:
                    nonFatalError(
                        f"ERROR: mismatched exclusive modifier types {lhs_type} and {rhs_type}"
                    )
                    break
                for type in modifier_priority_table[modifier]:
                    if type in lhs_type.modifiers or type in rhs_type.modifiers:
                        new_modifiers.append(type)
                        break

            # INCLUSIVE CLASS
            if ModifierClass.SIGN in lhs_class and ModifierClass.SIGN in rhs_class:
                if (
                    ModifierTypes.POSITIVE_TYPE in lhs_type.modifiers
                    and ModifierTypes.POSITIVE_TYPE in rhs_type.modifiers
                ):
                    pass
                elif (
                    ModifierTypes.NEGATIVE_TYPE in lhs_type.modifiers
                    and ModifierTypes.NEGATIVE_TYPE in rhs_type.modifiers
                ):
                    pass
                else:
                    pass
            elif ModifierClass.SIGN in lhs_class:
                pass
            elif ModifierClass.SIGN in rhs_class:
                pass

            if (
                ModifierClass.NONZERO in lhs_class
                and ModifierClass.NONZERO in rhs_class
            ):
                pass
            elif ModifierClass.NONZERO in lhs_class:
                pass
            elif ModifierClass.NONZERO in rhs_class:
                pass

            if ModifierClass.PARITY in lhs_class and ModifierClass.PARITY in rhs_class:
                if (
                    ModifierTypes.EVEN_TYPE in lhs_type.modifiers
                    and ModifierTypes.EVEN_TYPE in rhs_type.modifiers
                ):
                    new_modifiers.append(ModifierTypes.EVEN_TYPE)
                else:
                    new_modifiers.append(ModifierTypes.ODD_TYPE)
            elif ModifierClass.PARITY in lhs_class:
                pass
            elif ModifierClass.PARITY in rhs_class:
                pass
            tree.data.type = Type(builtin=new_builtin, modifiers=new_modifiers)
            return tree.data.type
        elif operator == ASTOperator.MULT_OPERATOR:
            if lhs_type.builtin in num_types or rhs_type.builtin in num_types:
                for int_type in num_types:
                    if lhs_type.builtin == int_type or rhs_type.builtin == int_type:
                        if lhs_type.builtin not in int_promotion_table[int_type]:
                            nonFatalError(
                                f"ERROR: Invalid lhs operand {lhs_type} must be numerical type"
                            )
                            break
                        elif rhs_type.builtin not in int_promotion_table[int_type]:
                            nonFatalError(
                                f"ERROR: Invalid rhs operand {rhs_type} must be numerical type"
                            )
                            break
                        else:
                            new_builtin = int_type
                            break
            else:
                nonFatalError(
                    f"ERROR: Invalid operands {lhs_type}, {rhs_type} for binary operation"
                )

            lhs_class = getModifierClass(lhs_type.modifiers)
            rhs_class = getModifierClass(rhs_type.modifiers)

            lhs_exclusive = getExclusiveClass(lhs_class)
            rhs_exclusive = getExclusiveClass(rhs_class)
            # EXCLUSIVE CLASS
            if not lhs_exclusive and not rhs_exclusive:
                pass

            elif (
                lhs_exclusive == ModifierClass.VELOCITY
                and rhs_exclusive == ModifierClass.TIME
            ):
                if ModifierTypes.MPS_TYPE in lhs_type.modifiers:
                    new_modifiers.append(ModifierTypes.METER_TYPE)
                elif ModifierTypes.FPS_TYPE in lhs_type.modifiers:
                    new_modifiers.append(ModifierTypes.FT_TYPE)
            elif (
                lhs_exclusive == ModifierClass.TIME
                and rhs_exclusive == ModifierClass.VELOCITY
            ):
                if ModifierTypes.MPS_TYPE in rhs_type.modifiers:
                    new_modifiers.append(ModifierTypes.METER_TYPE)
                elif ModifierTypes.FPS_TYPE in rhs_type.modifiers:
                    new_modifiers.append(ModifierTypes.FT_TYPE)

            elif (
                lhs_exclusive == ModifierClass.ACCELERATION
                and rhs_exclusive == ModifierClass.TIME
            ):
                if ModifierTypes.MPS2_TYPE in lhs_type.modifiers:
                    new_modifiers.append(ModifierTypes.MPS_TYPE)
            elif (
                lhs_exclusive == ModifierClass.TIME
                and rhs_exclusive == ModifierClass.ACCELERATION
            ):
                if ModifierTypes.MPS2_TYPE in rhs_type.modifiers:
                    new_modifiers.append(ModifierTypes.MPS_TYPE)

            elif (
                lhs_exclusive == ModifierClass.PERCENT
                and rhs_exclusive == ModifierClass.PERCENT
            ):
                for type in modifier_priority_table[lhs_exclusive]:
                    if type in lhs_type.modifiers or type in rhs_type.modifiers:
                        new_modifiers.append(type)
                        break
            elif not lhs_exclusive and rhs_exclusive == ModifierClass.PERCENT:
                for type in modifier_priority_table[rhs_exclusive]:
                    if type in rhs_type.modifiers:
                        new_modifiers.append(type)
                        break
            elif lhs_exclusive == ModifierClass.PERCENT and not rhs_exclusive:
                for type in modifier_priority_table[lhs_exclusive]:
                    if type in lhs_type.modifiers:
                        new_modifiers.append(type)
                        break

            elif (
                lhs_exclusive == ModifierClass.DISTANCE
                and rhs_exclusive == ModifierClass.DISTANCE
            ):
                for type in modifier_priority_table[lhs_exclusive]:
                    if type in lhs_type.modifiers or type in rhs_type.modifiers:
                        new_modifiers.append(distance_to_area[type])
                        break

            elif (
                lhs_exclusive == ModifierClass.DISTANCE
                and rhs_exclusive == ModifierClass.AREA
            ):
                for i in range(len(modifier_priority_table[lhs_exclusive])):
                    distance_type = modifier_priority_table[lhs_exclusive][i]
                    area_type = modifier_priority_table[rhs_exclusive][i]
                    if distance_type in lhs_type.modifiers:
                        new_modifiers.append(distance_or_area_to_volume[distance_type])
                        break
                    if area_type in rhs_type.modifiers:
                        new_modifiers.append(distance_or_area_to_volume[area_type])
                        break
            elif (
                lhs_exclusive == ModifierClass.AREA
                and rhs_exclusive == ModifierClass.DISTANCE
            ):
                for i in range(len(modifier_priority_table[lhs_exclusive])):
                    area_type = modifier_priority_table[lhs_exclusive][i]
                    distance_type = modifier_priority_table[rhs_exclusive][i]
                    if area_type in lhs_type.modifiers:
                        new_modifiers.append(distance_or_area_to_volume[area_type])
                        break
                    if distance_type in rhs_type.modifiers:
                        new_modifiers.append(distance_or_area_to_volume[distance_type])
                        break

            elif (
                lhs_exclusive == ModifierClass.MASS
                and rhs_exclusive == ModifierClass.ACCELERATION
            ) or (
                lhs_exclusive == ModifierClass.ACCELERATION
                and rhs_exclusive == ModifierClass.MASS
            ):
                new_modifiers.append(ModifierTypes.NEWT_TYPE)

            elif lhs_exclusive and not rhs_exclusive:
                for type in modifier_priority_table[lhs_exclusive]:
                    if type in lhs_type.modifiers:
                        new_modifiers.append(type)
                        break

            elif not lhs_exclusive and rhs_exclusive:
                for type in modifier_priority_table[rhs_exclusive]:
                    if type in rhs_type.modifiers:
                        new_modifiers.append(type)
                        break
            else:
                nonFatalError(
                    f"ERROR: invalid operand class for multiplication {lhs_exclusive} and {rhs_exclusive}, type {lhs_type} and {rhs_type}"
                )

            # INCLUSIVE CLASS
            if ModifierClass.SIGN in lhs_class and ModifierClass.SIGN in rhs_class:
                if (
                    ModifierTypes.POSITIVE_TYPE in lhs_type.modifiers
                    and ModifierTypes.POSITIVE_TYPE in rhs_type.modifiers
                ):
                    new_modifiers.append(ModifierTypes.POSITIVE_TYPE)
                elif (
                    ModifierTypes.NEGATIVE_TYPE in lhs_type.modifiers
                    and ModifierTypes.NEGATIVE_TYPE in rhs_type.modifiers
                ):
                    new_modifiers.append(ModifierTypes.POSITIVE_TYPE)
                elif (
                    ModifierTypes.POSITIVE_TYPE in lhs_type.modifiers
                    and ModifierTypes.NEGATIVE_TYPE in rhs_type.modifiers
                ):
                    new_modifiers.append(ModifierTypes.NEGATIVE_TYPE)
                elif (
                    ModifierTypes.NEGATIVE_TYPE in lhs_type.modifiers
                    and ModifierTypes.POSITIVE_TYPE in rhs_type.modifiers
                ):
                    new_modifiers.append(ModifierTypes.NEGATIVE_TYPE)
            elif ModifierClass.SIGN in lhs_class:
                pass
            elif ModifierClass.SIGN in rhs_class:
                pass

            if (
                ModifierClass.NONZERO in lhs_class
                and ModifierClass.NONZERO in rhs_class
            ):
                new_modifiers.append(ModifierTypes.NONZERO_TYPE)
            elif ModifierClass.NONZERO in lhs_class:
                pass
            elif ModifierClass.NONZERO in rhs_class:
                pass

            if ModifierClass.PARITY in lhs_class and ModifierClass.PARITY in rhs_class:
                if (
                    ModifierTypes.EVEN_TYPE in lhs_type.modifiers
                    and ModifierTypes.EVEN_TYPE in rhs_type.modifiers
                ):
                    new_modifiers.append(ModifierTypes.EVEN_TYPE)
                elif (
                    ModifierTypes.EVEN_TYPE in lhs_type.modifiers
                    and ModifierTypes.ODD_TYPE in rhs_type.modifiers
                ):
                    new_modifiers.append(ModifierTypes.EVEN_TYPE)
                elif (
                    ModifierTypes.ODD_TYPE in lhs_type.modifiers
                    and ModifierTypes.EVEN_TYPE in rhs_type.modifiers
                ):
                    new_modifiers.append(ModifierTypes.EVEN_TYPE)
                else:
                    new_modifiers.append(ModifierTypes.ODD_TYPE)
            elif ModifierClass.PARITY in lhs_class:
                pass
            elif ModifierClass.PARITY in rhs_class:
                pass
            tree.data.type = Type(builtin=new_builtin, modifiers=new_modifiers)
            return tree.data.type
        elif operator == ASTOperator.DIV_OPERATOR:
            if lhs_type.builtin in num_types or rhs_type.builtin in num_types:
                for int_type in num_types:
                    if lhs_type.builtin == int_type or rhs_type.builtin == int_type:
                        if lhs_type.builtin not in int_promotion_table[int_type]:
                            nonFatalError(
                                f"ERROR: Invalid lhs operand {lhs_type} must be numerical type"
                            )
                            break
                        elif rhs_type.builtin not in int_promotion_table[int_type]:
                            nonFatalError(
                                f"ERROR: Invalid rhs operand {rhs_type} must be numerical type"
                            )
                            break
                        else:
                            new_builtin = int_type
                            break
            else:
                nonFatalError(
                    f"ERROR: Invalid operands {lhs_type}, {rhs_type} for binary operation"
                )

            lhs_class = getModifierClass(lhs_type.modifiers)
            rhs_class = getModifierClass(rhs_type.modifiers)

            lhs_exclusive = getExclusiveClass(lhs_class)
            rhs_exclusive = getExclusiveClass(rhs_class)

            # EXCLUSIVE CLASS
            if not lhs_exclusive and not rhs_exclusive:
                pass

            elif lhs_exclusive and not rhs_exclusive:
                for type in modifier_priority_table[lhs_exclusive]:
                    if type in lhs_type.modifiers:
                        new_modifiers.append(type)
                        break

            elif not lhs_exclusive and rhs_exclusive:
                nonFatalError("ERROR: lhs cannot be scalar in division")

            elif (
                lhs_exclusive == ModifierClass.PERCENT
                and rhs_exclusive == ModifierClass.PERCENT
            ):
                for type in modifier_priority_table[lhs_exclusive]:
                    if type in lhs_type.modifiers or type in rhs_type.modifiers:
                        new_modifiers.append(type)
                        break

            elif lhs_exclusive and rhs_exclusive and lhs_exclusive == rhs_exclusive:
                pass

            elif (
                lhs_exclusive == ModifierClass.DISTANCE
                and rhs_exclusive == ModifierClass.TIME
            ):
                if ModifierTypes.METER_TYPE in lhs_type.modifiers:
                    new_modifiers.append(ModifierTypes.MPS_TYPE)
                elif ModifierTypes.MM_TYPE in lhs_type.modifiers:
                    new_modifiers.append(ModifierTypes.MPS_TYPE)
                elif ModifierTypes.CM_TYPE in lhs_type.modifiers:
                    new_modifiers.append(ModifierTypes.MPS_TYPE)
                elif ModifierTypes.KM_TYPE in lhs_type.modifiers:
                    new_modifiers.append(ModifierTypes.MPS_TYPE)
                elif ModifierTypes.FT_TYPE in lhs_type.modifiers:
                    new_modifiers.append(ModifierTypes.FPS_TYPE)
                elif ModifierTypes.INCH_TYPE in lhs_type.modifiers:
                    new_modifiers.append(ModifierTypes.FPS_TYPE)

            elif (
                lhs_exclusive == ModifierClass.VELOCITY
                and rhs_exclusive == ModifierClass.TIME
            ):
                new_modifiers.append(ModifierTypes.MPS2_TYPE)

            elif (
                lhs_exclusive == ModifierClass.FORCE
                and rhs_exclusive == ModifierClass.MASS
            ):
                new_modifiers.append(ModifierTypes.MPS2_TYPE)

            elif (
                lhs_exclusive == ModifierClass.FORCE
                and rhs_exclusive == ModifierClass.ACCELERATION
            ):
                new_modifiers.append(ModifierTypes.KG_TYPE)

            elif (
                lhs_exclusive == ModifierClass.VOLUME
                and rhs_exclusive == ModifierClass.AREA
            ):
                for type in modifier_priority_table[rhs_exclusive]:
                    if type in rhs_type.modifiers:
                        new_modifiers.append(area_to_distance[type])
                        break

            elif (
                lhs_exclusive == ModifierClass.AREA
                and rhs_exclusive == ModifierClass.DISTANCE
            ):
                for i in range(len(modifier_priority_table[lhs_exclusive])):
                    area_type = modifier_priority_table[lhs_exclusive][i]
                    distance_type = modifier_priority_table[rhs_exclusive][i]
                    if area_type in lhs_type.modifiers:
                        new_modifiers.append(area_to_distance[area_type])
                        break
                    if distance_type in rhs_type.modifiers:
                        new_modifiers.append(distance_type)
                        break

            elif (
                lhs_exclusive == ModifierClass.VOLUME
                and rhs_exclusive == ModifierClass.DISTANCE
            ):
                for type in modifier_priority_table[rhs_exclusive]:
                    if type in rhs_type.modifiers:
                        new_modifiers.append(distance_to_area[type])
                        break

            else:
                nonFatalError(
                    f"ERROR: invalid operand class for division {lhs_exclusive} and {rhs_exclusive}, type {lhs_type} and {rhs_type}"
                )

            # INCLUSIVE CLASS
            if ModifierClass.SIGN in lhs_class and ModifierClass.SIGN in rhs_class:
                if (
                    ModifierTypes.POSITIVE_TYPE in lhs_type.modifiers
                    and ModifierTypes.POSITIVE_TYPE in rhs_type.modifiers
                ):
                    new_modifiers.append(ModifierTypes.POSITIVE_TYPE)
                elif (
                    ModifierTypes.NEGATIVE_TYPE in lhs_type.modifiers
                    and ModifierTypes.NEGATIVE_TYPE in rhs_type.modifiers
                ):
                    new_modifiers.append(ModifierTypes.POSITIVE_TYPE)
                elif (
                    ModifierTypes.POSITIVE_TYPE in lhs_type.modifiers
                    and ModifierTypes.NEGATIVE_TYPE in rhs_type.modifiers
                ):
                    new_modifiers.append(ModifierTypes.NEGATIVE_TYPE)
                elif (
                    ModifierTypes.NEGATIVE_TYPE in lhs_type.modifiers
                    and ModifierTypes.POSITIVE_TYPE in rhs_type.modifiers
                ):
                    new_modifiers.append(ModifierTypes.NEGATIVE_TYPE)
            elif ModifierClass.SIGN in lhs_class:
                pass
            elif ModifierClass.SIGN in rhs_class:
                pass

            if (
                ModifierClass.NONZERO in lhs_class
                and ModifierClass.NONZERO in rhs_class
            ):
                new_modifiers.append(ModifierTypes.NONZERO_TYPE)
            elif ModifierClass.NONZERO in lhs_class:
                pass
            elif ModifierClass.NONZERO in rhs_class:
                pass

            if ModifierClass.PARITY in lhs_class and ModifierClass.PARITY in rhs_class:
                if (
                    ModifierTypes.EVEN_TYPE in lhs_type.modifiers
                    and ModifierTypes.EVEN_TYPE in rhs_type.modifiers
                ):
                    pass
                elif (
                    ModifierTypes.EVEN_TYPE in lhs_type.modifiers
                    and ModifierTypes.ODD_TYPE in rhs_type.modifiers
                ):
                    pass
                elif (
                    ModifierTypes.ODD_TYPE in lhs_type.modifiers
                    and ModifierTypes.EVEN_TYPE in rhs_type.modifiers
                ):
                    pass
                else:
                    pass
            elif ModifierClass.PARITY in lhs_class:
                pass
            elif ModifierClass.PARITY in rhs_class:
                pass
            tree.data.type = Type(builtin=new_builtin, modifiers=new_modifiers)
            return tree.data.type
        elif operator == ASTOperator.MOD_OPERATOR:
            if lhs_type.builtin in int_types or rhs_type.builtin in int_types:
                for int_type in int_types:
                    if lhs_type.builtin == int_type or rhs_type.builtin == int_type:
                        if lhs_type.builtin not in int_promotion_table[int_type]:
                            nonFatalError(
                                f"ERROR: Invalid lhs operand {lhs_type} must be integral type"
                            )
                            break
                        elif rhs_type.builtin not in int_promotion_table[int_type]:
                            nonFatalError(
                                f"ERROR: Invalid rhs operand {rhs_type} must be integral type"
                            )
                            break
                        else:
                            new_builtin = int_type
                            break
            else:
                nonFatalError(
                    f"ERROR: Invalid operands {lhs_type}, {rhs_type} for binary operation"
                )

            lhs_class = getModifierClass(lhs_type.modifiers)
            rhs_class = getModifierClass(rhs_type.modifiers)

            lhs_exclusive = getExclusiveClass(lhs_class)
            rhs_exclusive = getExclusiveClass(rhs_class)
            # EXCLUSIVE CLASS
            if not lhs_exclusive and not rhs_exclusive:
                pass
            elif lhs_exclusive and rhs_exclusive and lhs_exclusive == rhs_exclusive:
                for type in modifier_priority_table[lhs_exclusive]:
                    if type in lhs_type.modifiers:
                        new_modifiers.append(type)
            else:
                nonFatalError(
                    f"ERROR: invalid operand class for modulo {lhs_exclusive} and {rhs_exclusive}, type {lhs_type} and {rhs_type}"
                )

            # INCLUSIVE CLASS
            if ModifierClass.SIGN in lhs_class and ModifierClass.SIGN in rhs_class:
                pass
            elif ModifierClass.SIGN in lhs_class:
                pass
            elif ModifierClass.SIGN in rhs_class:
                pass

            if (
                ModifierClass.NONZERO in lhs_class
                and ModifierClass.NONZERO in rhs_class
            ):
                pass
            elif ModifierClass.NONZERO in lhs_class:
                pass
            elif ModifierClass.NONZERO in rhs_class:
                pass

            if ModifierClass.PARITY in lhs_class and ModifierClass.PARITY in rhs_class:
                if (
                    ModifierTypes.EVEN_TYPE in lhs_type.modifiers
                    and ModifierTypes.EVEN_TYPE in rhs_type.modifiers
                ):
                    new_modifiers.append(ModifierTypes.EVEN_TYPE)
                elif (
                    ModifierTypes.EVEN_TYPE in lhs_type.modifiers
                    and ModifierTypes.ODD_TYPE in rhs_type.modifiers
                ):
                    pass
                elif (
                    ModifierTypes.ODD_TYPE in lhs_type.modifiers
                    and ModifierTypes.EVEN_TYPE in rhs_type.modifiers
                ):
                    new_modifiers.append(ModifierTypes.ODD_TYPE)
                else:
                    pass
            elif ModifierClass.PARITY in lhs_class:
                pass
            elif ModifierClass.PARITY in rhs_class:
                pass
            tree.data.type = Type(builtin=new_builtin, modifiers=new_modifiers)
            return tree.data.type
        elif operator == ASTOperator.EXP_OPERATOR:
            if lhs_type.builtin in num_types or rhs_type.builtin in num_types:
                for int_type in num_types:
                    if lhs_type.builtin == int_type or rhs_type.builtin == int_type:
                        if lhs_type.builtin not in int_promotion_table[int_type]:
                            nonFatalError(
                                f"ERROR: Invalid lhs operand {lhs_type} must be numerical type"
                            )
                            break
                        elif rhs_type.builtin not in int_promotion_table[int_type]:
                            nonFatalError(
                                f"ERROR: Invalid rhs operand {rhs_type} must be numerical type"
                            )
                            break
                        else:
                            new_builtin = int_type
                            break
            else:
                nonFatalError(
                    f"ERROR: Invalid operands {lhs_type}, {rhs_type} for binary operation"
                )

            lhs_class = getModifierClass(lhs_type.modifiers)
            rhs_class = getModifierClass(rhs_type.modifiers)

            lhs_exclusive = getExclusiveClass(lhs_class)
            rhs_exclusive = getExclusiveClass(rhs_class)
            # EXCLUSIVE CLASS
            if not lhs_exclusive and not rhs_exclusive:
                pass
            else:
                nonFatalError(
                    f"ERROR: invalid operand class for modulo {lhs_exclusive} and {rhs_exclusive}, type {lhs_type} and {rhs_type}"
                )

            # INCLUSIVE CLASS
            if ModifierClass.SIGN in lhs_class and ModifierClass.SIGN in rhs_class:
                if ModifierTypes.POSITIVE_TYPE in lhs_type.modifiers:
                    new_modifiers.append(ModifierTypes.POSITIVE_TYPE)
                elif ModifierTypes.EVEN_TYPE in rhs_type.modifiers:
                    new_modifiers.append(ModifierTypes.POSITIVE_TYPE)
                elif ModifierTypes.ODD_TYPE in rhs_type.modifiers:
                    new_modifiers.append(ModifierTypes.NEGATIVE_TYPE)
                elif lhs_type.builtin not in int_types:
                    nonFatalError(
                        f"ERROR: negative base for non integer exponent is invalid {lhs_type} and {rhs_type}"
                    )
            elif ModifierClass.SIGN in lhs_class:
                if ModifierTypes.POSITIVE_TYPE in lhs_type.modifiers:
                    new_modifiers.append(ModifierTypes.POSITIVE_TYPE)
                elif ModifierTypes.EVEN_TYPE in rhs_type.modifiers:
                    new_modifiers.append(ModifierTypes.POSITIVE_TYPE)
                elif ModifierTypes.ODD_TYPE in rhs_type.modifiers:
                    new_modifiers.append(ModifierTypes.NEGATIVE_TYPE)
                elif lhs_type.builtin not in int_types:
                    nonFatalError(
                        f"ERROR: negative base for non integer exponent is invalid {lhs_type} and {rhs_type}"
                    )
            elif ModifierClass.SIGN in rhs_class:
                pass

            if ModifierClass.NONZERO in lhs_class:
                if (
                    ModifierTypes.NEGATIVE_TYPE in lhs_type.modifiers
                    and rhs_type.builtin not in int_types
                ):
                    nonFatalError(
                        f"ERROR: negative base for non integer exponent is invalid {lhs_type} and {rhs_type}"
                    )
                else:
                    new_modifiers.append(ModifierTypes.NONZERO_TYPE)
            elif ModifierClass.NONZERO in rhs_class:
                pass

            if ModifierClass.PARITY in lhs_class and ModifierClass.PARITY in rhs_class:
                if (
                    ModifierTypes.EVEN_TYPE in lhs_type.modifiers
                    and ModifierTypes.NONZERO_TYPE in rhs_type.modifiers
                    and ModifierTypes.POSITIVE_TYPE in rhs_type.modifiers
                ):
                    new_modifiers.append(ModifierTypes.EVEN_TYPE)
                elif (
                    ModifierTypes.ODD_TYPE in lhs_type.modifiers
                    and ModifierTypes.NONZERO_TYPE in rhs_type.modifiers
                    and ModifierTypes.POSITIVE_TYPE in rhs_type.modifiers
                ):
                    new_modifiers.append(ModifierTypes.ODD_TYPE)
                else:
                    pass
            elif ModifierClass.PARITY in lhs_class:
                pass
            elif ModifierClass.PARITY in rhs_class:
                pass
            tree.data.type = Type(builtin=new_builtin, modifiers=new_modifiers)
            return tree.data.type
        elif operator in [
            ASTOperator.NOT_EQUAL_OPERATOR,
            ASTOperator.EQUAL_OPERATOR,
        ]:
            new_builtin = BuiltInTypes.BOOL_TYPE
            lhs_class = getModifierClass(lhs_type.modifiers)
            rhs_class = getModifierClass(rhs_type.modifiers)

            for modifier in modifier_priority_table.keys():
                if modifier not in lhs_class and modifier not in rhs_class:
                    continue
                if modifier not in lhs_class or modifier not in rhs_class:
                    nonFatalError(
                        f"ERROR: mismatched exclusive modifier types {lhs_type} and {rhs_type}"
                    )
                    break

            tree.data.type = Type(builtin=new_builtin, modifiers=new_modifiers)
            return tree.data.type
        elif operator in [
            ASTOperator.LESS_OPERATOR,
            ASTOperator.LESS_OR_EQUAL_OPERATOR,
            ASTOperator.GREATER_OPERATOR,
            ASTOperator.GREATER_OR_EQUAL_OPERATOR,
        ]:
            new_builtin = BuiltInTypes.BOOL_TYPE
            if (
                lhs_type.builtin == BuiltInTypes.STRING_TYPE
                or rhs_type.builtin == BuiltInTypes.STRING_TYPE
            ):
                nonFatalError(
                    f"ERROR: string is invalid for comparison operation {lhs_type} and {rhs_type}"
                )
                return Type(builtin=new_builtin)
            lhs_class = getModifierClass(lhs_type.modifiers)
            rhs_class = getModifierClass(rhs_type.modifiers)

            for modifier in modifier_priority_table.keys():
                if modifier not in lhs_class and modifier not in rhs_class:
                    continue
                if modifier not in lhs_class or modifier not in rhs_class:
                    nonFatalError(
                        f"ERROR: mismatched exclusive modifier types {lhs_type} and {rhs_type}"
                    )
                    break

            tree.data.type = Type(builtin=new_builtin)
            return tree.data.type
        elif operator == ASTOperator.AND_OPERATOR:
            new_builtin = BuiltInTypes.BOOL_TYPE
            tree.data.type = Type(builtin=new_builtin)
            return tree.data.type
        elif operator == ASTOperator.OR_OPERATOR:
            new_builtin = BuiltInTypes.BOOL_TYPE
            tree.data.type = Type(builtin=new_builtin)
            return tree.data.type
        elif operator == ASTOperator.ASSIGNMENT_OPERATOR:
            if lhs.kind != ASTNodeType.IDENTIFIER:
                nonFatalError("ERROR: left side of assignment must be l-value")
                return lhs_type
            if not isTypeCastable(lhs_type, rhs_type):
                nonFatalError(f"ERROR: {lhs_type} is not assignable to {rhs}")
            tree.data.type = lhs_type
            return tree.data.type

        elif operator in [
            ASTOperator.PLUS_ASSIGNMENT_OPERATOR,
            ASTOperator.MINUS_ASSIGNMENT_OPERATOR,
            ASTOperator.MULTIPLY_ASSIGNMENT_OPERATOR,
            ASTOperator.DIVIDE_ASSIGNMENT_OPERATOR,
            ASTOperator.MODULO_ASSIGNMENT_OPERATOR,
        ]:
            compound_assignment_to_operator = {
                ASTOperator.PLUS_ASSIGNMENT_OPERATOR: ASTOperator.ADD_OPERATOR,
                ASTOperator.MINUS_ASSIGNMENT_OPERATOR: ASTOperator.SUB_OPERATOR,
                ASTOperator.MULTIPLY_ASSIGNMENT_OPERATOR: ASTOperator.MULT_OPERATOR,
                ASTOperator.DIVIDE_ASSIGNMENT_OPERATOR: ASTOperator.DIV_OPERATOR,
                ASTOperator.MODULO_ASSIGNMENT_OPERATOR: ASTOperator.MOD_OPERATOR,
            }
            pseudo_binary_op_node = ASTNode(
                kind=ASTNodeType.BINARY_OP,
                token=tree.token,
                data=BinaryOpData(
                    lhs=lhs, rhs=rhs, operator=compound_assignment_to_operator[operator]
                ),
            )
            pseudo_assignment_op_node = ASTNode(
                kind=ASTNodeType.BINARY_OP,
                token=tree.token,
                data=BinaryOpData(
                    lhs=lhs,
                    rhs=pseudo_binary_op_node,
                    operator=ASTOperator.ASSIGNMENT_OPERATOR,
                ),
            )
            tree.data.type = resolveBinaryOp(pseudo_assignment_op_node, scope)
            return tree.data.type
        elif operator in [
            ASTOperator.PERCENT_SCALE_OPERATOR,
            ASTOperator.MARKUP_OPERATOR,
            ASTOperator.MARKDOWN_OPERATOR,
        ]:
            if lhs_type.builtin in num_types or rhs_type.builtin in num_types:
                for int_type in num_types:
                    if lhs_type.builtin == int_type or rhs_type.builtin == int_type:
                        if lhs_type.builtin not in int_promotion_table[int_type]:
                            nonFatalError(
                                f"ERROR: Invalid lhs operand {lhs_type} must be numerical type"
                            )
                            break
                        elif rhs_type.builtin not in int_promotion_table[int_type]:
                            nonFatalError(
                                f"ERROR: Invalid rhs operand {rhs_type} must be numerical type"
                            )
                            break
                        else:
                            new_builtin = int_type
                            break
            else:
                nonFatalError(
                    f"ERROR: Invalid operands {lhs_type}, {rhs_type} for binary operation"
                )

            lhs_class = getModifierClass(lhs_type.modifiers)
            rhs_class = getModifierClass(rhs_type.modifiers)

            lhs_exclusive = getExclusiveClass(lhs_class)
            rhs_exclusive = getExclusiveClass(rhs_class)

            if rhs_exclusive == ModifierClass.PERCENT:
                tree.data.type = lhs_type
                return tree.data.type
            elif not rhs_exclusive:
                tree.data.type = lhs_type
                return tree.data.type
            else:
                nonFatalError(
                    f"ERROR: Invalid rhs operand {rhs_type} must be either percent or scalar"
                )
        return Type(builtin=BuiltInTypes.VOID_TYPE)

    def resolveUnaryOp(tree: ASTNode, scope: Scope) -> Type:
        operand = tree.data.operand
        operand_type = resolveExpression(operand, scope)
        operator = tree.data.operator
        if operand_type.builtin == BuiltInTypes.VOID_TYPE:
            nonFatalError("ERROR: void type is invalid operand for unary operation")
            return Type(builtin=BuiltInTypes.VOID_TYPE)
        elif operator == ASTOperator.POSITIVE_OPERATOR:
            if operand.builtin not in num_types:
                nonFatalError(
                    f"ERROR: Invalid operand {operand} must be numerical type"
                )
                return Type(builtin=BuiltInTypes.VOID_TYPE)
            tree.data.type = operand_type
            return tree.data.type
        elif operator == ASTOperator.NEGATIVE_OPERATOR:
            operand_type_copy = copy.deepcopy(operand_type)
            if operand.builtin not in num_types:
                nonFatalError(
                    f"ERROR: Invalid operand {operand} must be numerical type"
                )
                return Type(builtin=BuiltInTypes.VOID_TYPE)
            if ModifierTypes.POSITIVE_TYPE in operand_type_copy.modifiers:
                operand_type_copy.modifiers.remove(ModifierTypes.POSITIVE_TYPE)
                operand_type_copy.modifiers.append(ModifierTypes.NEGATIVE_TYPE)
            tree.data.type = operand_type_copy
            return tree.data.type
        elif operator in [
            ASTOperator.PRE_INCREMENT_OPERATOR,
            ASTOperator.PRE_DECREMENT_OPERATOR,
        ]:
            if operand.kind != ASTNodeType.IDENTIFIER:
                nonFatalError("ERROR: left side of assignment must be l-value")
                return operand_type
            if operand_type.builtin not in int_types:
                nonFatalError(f"ERROR: Invalid operand {operand} must be integral type")
                return Type(builtin=BuiltInTypes.VOID_TYPE)
            tree.data.type = operand_type
            return tree.data.type
        elif operator in [
            ASTOperator.POST_INCREMENT_OPERATOR,
            ASTOperator.POST_DECREMENT_OPERATOR,
        ]:
            if operand.kind != ASTNodeType.IDENTIFIER:
                nonFatalError("ERROR: left side of assignment must be l-value")
                return operand_type
            if operand.builtin not in int_types:
                nonFatalError(f"ERROR: Invalid operand {operand} must be integral type")
                return Type(builtin=BuiltInTypes.VOID_TYPE)
            tree.data.type = operand_type
            return tree.data.type
        elif operator == ASTOperator.NOT_OPERATOR:
            tree.data.type = Type(builtin=BuiltInTypes.BOOL_TYPE)
            return tree.data.type
        return Type(builtin=BuiltInTypes.VOID_TYPE)

    def resolveFunctionCall(tree: ASTNode, scope: Scope) -> Type:
        name = resolveIdentifier(tree.data.function, scope)
        symbol = reference(scope, name, True)
        if not symbol:
            return Type(builtin=BuiltInTypes.VOID_TYPE)
        if not isinstance(symbol.type, Function):
            nonFatalError(f"ERROR: '{name}' is not callable")
            return Type(builtin=BuiltInTypes.VOID_TYPE)

        arguments: list[Type] = []
        for arg in tree.data.arguments:
            arguments.append(resolveExpression(arg, scope))

        parameters: list[Type] = []
        for param in symbol.type.parameters:
            parameters.append(param.type)

        if len(parameters) != len(arguments):
            nonFatalError(f"ERROR: expected {len(parameters)} argument(s)")
            return symbol.type.return_type

        for i in range(len(arguments)):
            arg = arguments[i]
            param = parameters[i]
            if not isTypeCastable(param, arg):
                nonFatalError(
                    f"ERROR: Argument type {arg} cannot be assigned to parameter type {param}"
                )
        tree.data.type = symbol.type.return_type
        return tree.data.type

    def resolveArrayIndex(tree: ASTNode, scope: Scope) -> Type:
        if tree.data.array:
            array = resolveExpression(tree.data.array, scope)
            tree.data.type = array
            return tree.data.type

    def resolveLiteral(tree: ASTNode, scope: Scope) -> Type:
        if tree.data.literal_type == ASTLiteral.TRUE_LITERAL:
            tree.data.type = Type(builtin=BuiltInTypes.BOOL_TYPE)
        elif tree.data.literal_type == ASTLiteral.FALSE_LITERAL:
            tree.data.type = Type(builtin=BuiltInTypes.BOOL_TYPE)
        elif tree.data.literal_type == ASTLiteral.INT_LITERAL:
            tree.data.type = Type(builtin=BuiltInTypes.INT_TYPE)
        elif tree.data.literal_type == ASTLiteral.FLOAT_LITERAL:
            tree.data.type = Type(builtin=BuiltInTypes.FLOAT_TYPE)
        elif tree.data.literal_type == ASTLiteral.CHAR_LITERAL:
            tree.data.type = Type(builtin=BuiltInTypes.CHAR_TYPE)
        elif tree.data.literal_type == ASTLiteral.STRING_LITERAL:
            tree.data.type = Type(builtin=BuiltInTypes.STRING_TYPE)
        assert tree.data.type
        return tree.data.type

    def resolveSymbol(tree: ASTNode, scope: Scope) -> Type | Function:
        name = resolveIdentifier(tree, scope)
        symbol = reference(scope, name, True)
        if not symbol:
            return Type(builtin=BuiltInTypes.VOID_TYPE)
        return symbol.type

    def resolveType(type: Type, scope: Scope) -> Type | None:
        if (
            type.builtin not in [BuiltInTypes.INT_TYPE, BuiltInTypes.FLOAT_TYPE]
            and len(type.modifiers) > 0
        ):
            nonFatalError(f"ERROR: type {type} cannot have modifier types")
            return
        filtered_modifiers = set()
        has_percent = False
        has_sign = False
        has_nonzero = False  # non-dependent
        has_parity = False
        has_auto = False
        has_time = False
        has_distance = False
        has_area = False
        has_volume = False
        has_mass = False
        has_temp = False
        has_force = False
        has_velocity = False
        has_accel = False  # non-dependent

        for modifier in type.modifiers:
            if modifier in filtered_modifiers:
                nonFatalError("ERROR: Duplicate modifier in compound type")
            if modifier in percent_types:
                if has_percent:
                    nonFatalError(
                        "ERROR: Multiple modifier in same type category (percent)"
                    )
                has_percent = True
            elif modifier in sign_types:
                if has_sign:
                    nonFatalError(
                        "ERROR: Multiple modifier in same type category (sign)"
                    )
                has_sign = True
            elif modifier in nonzero_types:
                has_nonzero = True
            elif modifier in parity_types:
                if has_parity:
                    nonFatalError(
                        "ERROR: Multiple modifier in same type category (parity)"
                    )
                has_parity = True
            elif modifier in time_types:
                if has_time:
                    nonFatalError(
                        "ERROR: Multiple modifier in same type category (time)"
                    )
                has_time = True
            elif modifier in distance_types:
                if has_distance:
                    nonFatalError(
                        "ERROR: Multiple modifier in same type category (distance)"
                    )
                has_distance = True
            elif modifier in area_types:
                if has_area:
                    nonFatalError(
                        "ERROR: Multiple modifier in same type category (area)"
                    )
                has_area = True
            elif modifier in volume_types:
                if has_volume:
                    nonFatalError(
                        "ERROR: Multiple modifier in same type category (volume)"
                    )
                has_volume = True
            elif modifier in mass_types:
                if has_mass:
                    nonFatalError(
                        "ERROR: Multiple modifier in same type category (mass)"
                    )
                has_mass = True
            elif modifier in temp_types:
                if has_temp:
                    nonFatalError(
                        "ERROR: Multiple modifier in same type category (temperature)"
                    )
                has_temp = True
            elif modifier in force_types:
                if has_force:
                    nonFatalError(
                        "ERROR: Multiple modifier in same type category (force)"
                    )
                has_force = True
            elif modifier in velocity_types:
                if has_velocity:
                    nonFatalError(
                        "ERROR: Multiple modifier in same type category (velocity)"
                    )
                has_velocity = True
            elif modifier in accel_types:
                if has_accel:
                    nonFatalError(
                        "ERROR: Multiple modifier in same type category (acceleration)"
                    )
                has_accel = True
            elif modifier in auto_type:
                if (
                    has_percent
                    or has_sign
                    or has_nonzero
                    or has_parity
                    or has_time
                    or has_distance
                    or has_area
                    or has_volume
                    or has_mass
                    or has_temp
                    or has_force
                    or has_velocity
                    or has_accel
                ):
                    nonFatalError("ERROR: Auto modifier cannot be with other modifiers")

            filtered_modifiers.add(modifier)
        modifier_classes = getModifierClass(type.modifiers)

        def filterExclusive(modifier_class: ModifierClass):
            return modifier_class in [
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

        modifier_classes = list(filter(filterExclusive, modifier_classes))
        if len(modifier_classes) > 1:
            names = ", ".join(m.name for m in modifier_classes)
            nonFatalError(f"ERROR: Modifier types {names} are exclusive")
        if type.builtin == BuiltInTypes.FLOAT_TYPE and has_parity:
            nonFatalError("ERROR: Parity type cannot be floating point")

    def isTypeMatched(type1: Type, type2: Type) -> bool:
        if type1.builtin != type2.builtin:
            return False
        return Counter(type1.modifiers) == Counter(type2.modifiers)

    def isTypeCastable(dest: Type, src: Type) -> bool:
        if dest.builtin == src.builtin and Counter(dest.modifiers) == Counter(
            src.modifiers
        ):
            return True
        is_builtin_castable = False
        if dest.builtin == src.builtin:
            is_builtin_castable = True
        elif dest.builtin in num_types and src.builtin in num_types:
            is_builtin_castable = True
        elif (
            dest.builtin == BuiltInTypes.INT_TYPE
            and src.builtin == BuiltInTypes.FLOAT_TYPE
        ):
            is_builtin_castable = True
        elif dest.builtin == BuiltInTypes.BOOL_TYPE and src.builtin in [
            BuiltInTypes.INT_TYPE,
            BuiltInTypes.FLOAT_TYPE,
            BuiltInTypes.BOOL_TYPE,
            BuiltInTypes.CHAR_TYPE,
            BuiltInTypes.STRING_TYPE,
        ]:
            is_builtin_castable = True
        else:
            return False
        dest_class = getModifierClass(dest.modifiers)
        src_class = getModifierClass(src.modifiers)
        if len(src_class) == 0:
            return True
        if dest_class != src_class:
            return False
        if ModifierClass.AUTO in dest_class:
            nonFatalError("ERROR: Not bounded auto type is not type castable")
            return False
        if ModifierClass.AUTO in src_class:
            nonFatalError("ERROR: Not bounded auto type is not type castable")
            return False
        return True

    def getExclusiveClass(
        modifier_classes: set[ModifierClass],
    ) -> ModifierClass | None:
        for modifier_class in modifier_classes:
            if modifier_class in exclusive_class:
                return modifier_class

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

    assert tree.kind == ASTNodeType.FILE
    for node in tree.data.children:
        if node.kind == ASTNodeType.FUNCTION_STMT:
            resolveFunctionStmt(node, scope)
        elif node.kind == ASTNodeType.DECLARATION:
            resolveDeclaration(node, scope)
    return scope, has_error
