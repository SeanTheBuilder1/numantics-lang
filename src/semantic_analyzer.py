from __future__ import annotations
from semantic_types import (
    BuiltInTypes,
    ExclusiveUnit,
    Function,
    ModifierClass,
    ModifierTypes,
    Parameter,
    Scope,
    Symbol,
    Type,
)
from type_functions import getExclusiveClass, getModifierClass
from ast_types import ASTLiteral, ASTNode, ASTNodeType, ASTOperator, BinaryOpData
from collections import Counter
from enum import Enum, auto
from dataclasses import dataclass
from unit_functions import createUnitOnlyType, unitConversionResultsInFloat
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
    distance_to_area,
    distance_or_area_to_volume,
    area_to_distance,
    volume_to_distance_and_area,
    int_promotion_table,
    num_types,
    int_types,
    modifier_priority_table,
    distance_to_area_and_volume,
    area_to_distance_and_volume,
    distance_to_velocity,
)
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
        new_type = Type(builtin=BuiltInTypes.VOID_TYPE, modifiers=[])

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
                    new_type.builtin = BuiltInTypes.STRING_TYPE
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
                            new_type.builtin = int_type
                            break

            lhs_class = getModifierClass(lhs_type.modifiers)
            rhs_class = getModifierClass(rhs_type.modifiers)

            # EXCLUSIVE CLASS
            if bool(lhs_type.exclusive) ^ bool(rhs_type.exclusive):
                nonFatalError(
                    f"ERROR: mismatched exclusive modifier types {lhs_type.exclusive} and {rhs_type.exclusive}"
                )
            elif lhs_type.exclusive and rhs_type.exclusive:
                if lhs_type.exclusive.unit_class != rhs_type.exclusive.unit_class:
                    nonFatalError(
                        f"ERROR: mismatched exclusive modifier types {lhs_type.exclusive} and {rhs_type.exclusive}"
                    )
                for type in modifier_priority_table[lhs_type.exclusive.unit_class]:
                    if (
                        type == lhs_type.exclusive.unit
                        or type == rhs_type.exclusive.unit
                    ):
                        if (
                            lhs_type.exclusive.unit_class == ModifierClass.TEMP
                            and lhs_type.exclusive.unit != rhs_type.exclusive.unit
                        ):
                            nonFatalError(
                                f"ERROR: addition of temperatures must have matching units {lhs_type.exclusive.unit} and {rhs_type.exclusive.unit}"
                            )
                            new_type.builtin = BuiltInTypes.VOID_TYPE
                            break

                        dest_type = (
                            lhs_type if type == lhs_type.exclusive.unit else rhs_type
                        )
                        src_type = (
                            rhs_type if type == lhs_type.exclusive.unit else lhs_type
                        )
                        if unitConversionResultsInFloat(dest_type, src_type):
                            new_type.builtin = BuiltInTypes.FLOAT_TYPE
                        new_type.exclusive = ExclusiveUnit(
                            unit=type, unit_class=lhs_type.exclusive.unit_class
                        )
                        new_type.modifiers.append(type)
                        break

            # INCLUSIVE CLASS
            if ModifierClass.SIGN in lhs_class and ModifierClass.SIGN in rhs_class:
                if (
                    ModifierTypes.POSITIVE_TYPE in lhs_type.modifiers
                    and ModifierTypes.POSITIVE_TYPE in rhs_type.modifiers
                ):
                    new_type.modifiers.append(ModifierTypes.POSITIVE_TYPE)
                elif (
                    ModifierTypes.NEGATIVE_TYPE in lhs_type.modifiers
                    and ModifierTypes.NEGATIVE_TYPE in rhs_type.modifiers
                ):
                    new_type.modifiers.append(ModifierTypes.NEGATIVE_TYPE)
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
                    new_type.modifiers.append(ModifierTypes.EVEN_TYPE)
                else:
                    new_type.modifiers.append(ModifierTypes.ODD_TYPE)
            elif ModifierClass.PARITY in lhs_class:
                pass
            elif ModifierClass.PARITY in rhs_class:
                pass
            tree.data.type = new_type
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
                            new_type.builtin = int_type
                            break
            else:
                nonFatalError(
                    f"ERROR: Invalid operands {lhs_type}, {rhs_type} for binary operation"
                )

            lhs_class = getModifierClass(lhs_type.modifiers)
            rhs_class = getModifierClass(rhs_type.modifiers)

            # EXCLUSIVE CLASS
            if bool(lhs_type.exclusive) ^ bool(rhs_type.exclusive):
                nonFatalError(
                    f"ERROR: mismatched exclusive modifier types {lhs_type.exclusive} and {rhs_type.exclusive}"
                )
            elif lhs_type.exclusive and rhs_type.exclusive:
                if lhs_type.exclusive.unit_class != rhs_type.exclusive.unit_class:
                    nonFatalError(
                        f"ERROR: mismatched exclusive modifier types {lhs_type.exclusive} and {rhs_type.exclusive}"
                    )
                for type in modifier_priority_table[lhs_type.exclusive.unit_class]:
                    if (
                        type == lhs_type.exclusive.unit
                        or type == rhs_type.exclusive.unit
                    ):
                        dest_type = (
                            lhs_type if type == lhs_type.exclusive.unit else rhs_type
                        )
                        src_type = (
                            rhs_type if type == lhs_type.exclusive.unit else lhs_type
                        )
                        if unitConversionResultsInFloat(dest_type, src_type):
                            new_type.builtin = BuiltInTypes.FLOAT_TYPE
                        new_type.exclusive = ExclusiveUnit(
                            unit=type, unit_class=lhs_type.exclusive.unit_class
                        )
                        new_type.modifiers.append(type)
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
                    new_type.modifiers.append(ModifierTypes.EVEN_TYPE)
                else:
                    new_type.modifiers.append(ModifierTypes.ODD_TYPE)
            elif ModifierClass.PARITY in lhs_class:
                pass
            elif ModifierClass.PARITY in rhs_class:
                pass
            tree.data.type = new_type
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
                            new_type.builtin = int_type
                            break
            else:
                nonFatalError(
                    f"ERROR: Invalid operands {lhs_type}, {rhs_type} for binary operation"
                )

            lhs_class = getModifierClass(lhs_type.modifiers)
            rhs_class = getModifierClass(rhs_type.modifiers)

            lhs_exclusive = (
                lhs_type.exclusive.unit_class if lhs_type.exclusive else None
            )
            rhs_exclusive = (
                rhs_type.exclusive.unit_class if rhs_type.exclusive else None
            )

            # EXCLUSIVE CLASS
            if not lhs_exclusive and not rhs_exclusive:
                pass

            elif (
                lhs_exclusive == ModifierClass.VELOCITY
                and rhs_exclusive == ModifierClass.TIME
            ):
                second_unit = createUnitOnlyType(ModifierTypes.SECOND_TYPE)
                if ModifierTypes.MPS_TYPE in lhs_type.modifiers:
                    new_type.modifiers.append(ModifierTypes.METER_TYPE)
                    new_type.exclusive = ExclusiveUnit(
                        unit=ModifierTypes.METER_TYPE, unit_class=ModifierClass.DISTANCE
                    )
                elif ModifierTypes.FPS_TYPE in lhs_type.modifiers:
                    new_type.modifiers.append(ModifierTypes.FT_TYPE)
                    new_type.exclusive = ExclusiveUnit(
                        unit=ModifierTypes.FT_TYPE, unit_class=ModifierClass.DISTANCE
                    )
                if unitConversionResultsInFloat(second_unit, rhs_type):
                    new_type.builtin = BuiltInTypes.FLOAT_TYPE
            elif (
                lhs_exclusive == ModifierClass.TIME
                and rhs_exclusive == ModifierClass.VELOCITY
            ):
                second_unit = createUnitOnlyType(ModifierTypes.SECOND_TYPE)
                if ModifierTypes.MPS_TYPE in rhs_type.modifiers:
                    new_type.modifiers.append(ModifierTypes.METER_TYPE)
                    new_type.exclusive = ExclusiveUnit(
                        unit=ModifierTypes.METER_TYPE, unit_class=ModifierClass.DISTANCE
                    )
                elif ModifierTypes.FPS_TYPE in rhs_type.modifiers:
                    new_type.modifiers.append(ModifierTypes.FT_TYPE)
                    new_type.exclusive = ExclusiveUnit(
                        unit=ModifierTypes.FT_TYPE, unit_class=ModifierClass.DISTANCE
                    )
                if unitConversionResultsInFloat(second_unit, lhs_type):
                    new_type.builtin = BuiltInTypes.FLOAT_TYPE

            elif (
                lhs_exclusive == ModifierClass.ACCELERATION
                and rhs_exclusive == ModifierClass.TIME
            ):
                second_unit = createUnitOnlyType(ModifierTypes.SECOND_TYPE)
                if ModifierTypes.MPS2_TYPE in lhs_type.modifiers:
                    new_type.modifiers.append(ModifierTypes.MPS_TYPE)
                    new_type.exclusive = ExclusiveUnit(
                        unit=ModifierTypes.MPS_TYPE, unit_class=ModifierClass.VELOCITY
                    )
                if unitConversionResultsInFloat(second_unit, rhs_type):
                    new_type.builtin = BuiltInTypes.FLOAT_TYPE
            elif (
                lhs_exclusive == ModifierClass.TIME
                and rhs_exclusive == ModifierClass.ACCELERATION
            ):
                second_unit = createUnitOnlyType(ModifierTypes.SECOND_TYPE)
                if ModifierTypes.MPS2_TYPE in rhs_type.modifiers:
                    new_type.modifiers.append(ModifierTypes.MPS_TYPE)
                    new_type.exclusive = ExclusiveUnit(
                        unit=ModifierTypes.MPS_TYPE, unit_class=ModifierClass.VELOCITY
                    )
                if unitConversionResultsInFloat(second_unit, lhs_type):
                    new_type.builtin = BuiltInTypes.FLOAT_TYPE

            elif (
                lhs_exclusive == ModifierClass.PERCENT
                and rhs_exclusive == ModifierClass.PERCENT
            ):
                for type in modifier_priority_table[lhs_exclusive]:
                    if type in lhs_type.modifiers or type in rhs_type.modifiers:
                        new_type.exclusive = ExclusiveUnit(
                            unit=type, unit_class=ModifierClass.PERCENT
                        )
                        new_type.modifiers.append(type)
                        break
                new_type.builtin = BuiltInTypes.FLOAT_TYPE
            elif (
                lhs_exclusive != ModifierClass.PERCENT
                and rhs_exclusive == ModifierClass.PERCENT
            ):
                if lhs_exclusive:
                    for type in modifier_priority_table[lhs_exclusive]:
                        if type in rhs_type.modifiers:
                            new_type.exclusive = ExclusiveUnit(
                                unit=type, unit_class=lhs_exclusive
                            )
                            new_type.modifiers.append(type)
                            break
                new_type.builtin = BuiltInTypes.FLOAT_TYPE
            elif (
                lhs_exclusive == ModifierClass.PERCENT
                and rhs_exclusive != ModifierClass.PERCENT
            ):
                if rhs_exclusive:
                    for type in modifier_priority_table[rhs_exclusive]:
                        if type in rhs_type.modifiers:
                            new_type.exclusive = ExclusiveUnit(
                                unit=type, unit_class=rhs_exclusive
                            )
                            new_type.modifiers.append(type)
                            break
                new_type.builtin = BuiltInTypes.FLOAT_TYPE

            elif (
                lhs_exclusive == ModifierClass.DISTANCE
                and rhs_exclusive == ModifierClass.DISTANCE
            ):
                for type in modifier_priority_table[lhs_exclusive]:
                    if type in lhs_type.modifiers or type in rhs_type.modifiers:
                        new_type.exclusive = ExclusiveUnit(
                            unit=distance_to_area[type], unit_class=ModifierClass.AREA
                        )
                        new_type.modifiers.append(distance_to_area[type])
                        dest_unit = createUnitOnlyType(type)
                        if unitConversionResultsInFloat(
                            dest_unit, lhs_type
                        ) or unitConversionResultsInFloat(dest_unit, rhs_type):
                            new_type.builtin = BuiltInTypes.FLOAT_TYPE
                        break

            elif (
                lhs_exclusive == ModifierClass.DISTANCE
                and rhs_exclusive == ModifierClass.AREA
            ):
                for i in range(len(modifier_priority_table[lhs_exclusive])):
                    distance_type = modifier_priority_table[lhs_exclusive][i]
                    area_type = modifier_priority_table[rhs_exclusive][i]
                    if distance_type in lhs_type.modifiers:
                        volume_type = distance_or_area_to_volume[distance_type]
                        new_type.modifiers.append(volume_type)
                        new_type.exclusive = ExclusiveUnit(
                            unit=volume_type, unit_class=ModifierClass.VOLUME
                        )
                        if volume_type == ModifierTypes.KL_TYPE:
                            meter_type = createUnitOnlyType(ModifierTypes.METER_TYPE)
                            meter2_type = createUnitOnlyType(ModifierTypes.METER2_TYPE)
                            if unitConversionResultsInFloat(
                                meter_type, lhs_type
                            ) or unitConversionResultsInFloat(meter2_type, rhs_type):
                                new_type.builtin = BuiltInTypes.FLOAT_TYPE
                        elif volume_type == ModifierTypes.ML_TYPE:
                            cm_type = createUnitOnlyType(ModifierTypes.CM_TYPE)
                            cm2_type = createUnitOnlyType(ModifierTypes.CM2_TYPE)
                            if unitConversionResultsInFloat(
                                cm_type, lhs_type
                            ) or unitConversionResultsInFloat(cm2_type, rhs_type):
                                new_type.builtin = BuiltInTypes.FLOAT_TYPE
                        break
                    elif area_type in rhs_type.modifiers:
                        volume_type = distance_or_area_to_volume[area_type]
                        new_type.modifiers.append(volume_type)
                        new_type.exclusive = ExclusiveUnit(
                            unit=volume_type, unit_class=ModifierClass.VOLUME
                        )
                        if volume_type == ModifierTypes.KL_TYPE:
                            meter_type = createUnitOnlyType(ModifierTypes.METER_TYPE)
                            meter2_type = createUnitOnlyType(ModifierTypes.METER2_TYPE)
                            if unitConversionResultsInFloat(
                                meter_type, lhs_type
                            ) or unitConversionResultsInFloat(meter2_type, rhs_type):
                                new_type.builtin = BuiltInTypes.FLOAT_TYPE
                        elif volume_type == ModifierTypes.ML_TYPE:
                            cm_type = createUnitOnlyType(ModifierTypes.CM_TYPE)
                            cm2_type = createUnitOnlyType(ModifierTypes.CM2_TYPE)
                            if unitConversionResultsInFloat(
                                cm_type, lhs_type
                            ) or unitConversionResultsInFloat(cm2_type, rhs_type):
                                new_type.builtin = BuiltInTypes.FLOAT_TYPE
                        break
            elif (
                lhs_exclusive == ModifierClass.AREA
                and rhs_exclusive == ModifierClass.DISTANCE
            ):
                for i in range(len(modifier_priority_table[lhs_exclusive])):
                    area_type = modifier_priority_table[lhs_exclusive][i]
                    distance_type = modifier_priority_table[rhs_exclusive][i]
                    if area_type in lhs_type.modifiers:
                        volume_type = distance_or_area_to_volume[distance_type]
                        new_type.modifiers.append(volume_type)
                        new_type.exclusive = ExclusiveUnit(
                            unit=volume_type, unit_class=ModifierClass.VOLUME
                        )
                        if volume_type == ModifierTypes.KL_TYPE:
                            meter_type = createUnitOnlyType(ModifierTypes.METER_TYPE)
                            meter2_type = createUnitOnlyType(ModifierTypes.METER2_TYPE)
                            if unitConversionResultsInFloat(
                                meter_type, rhs_type
                            ) or unitConversionResultsInFloat(meter2_type, lhs_type):
                                new_type.builtin = BuiltInTypes.FLOAT_TYPE
                        elif volume_type == ModifierTypes.ML_TYPE:
                            cm_type = createUnitOnlyType(ModifierTypes.CM_TYPE)
                            cm2_type = createUnitOnlyType(ModifierTypes.CM2_TYPE)
                            if unitConversionResultsInFloat(
                                cm_type, rhs_type
                            ) or unitConversionResultsInFloat(cm2_type, lhs_type):
                                new_type.builtin = BuiltInTypes.FLOAT_TYPE
                        break
                    elif distance_type in rhs_type.modifiers:
                        volume_type = distance_or_area_to_volume[area_type]
                        new_type.modifiers.append(volume_type)
                        new_type.exclusive = ExclusiveUnit(
                            unit=volume_type, unit_class=ModifierClass.VOLUME
                        )
                        if volume_type == ModifierTypes.KL_TYPE:
                            meter_type = createUnitOnlyType(ModifierTypes.METER_TYPE)
                            meter2_type = createUnitOnlyType(ModifierTypes.METER2_TYPE)
                            if unitConversionResultsInFloat(
                                meter_type, rhs_type
                            ) or unitConversionResultsInFloat(meter2_type, lhs_type):
                                new_type.builtin = BuiltInTypes.FLOAT_TYPE
                        elif volume_type == ModifierTypes.ML_TYPE:
                            cm_type = createUnitOnlyType(ModifierTypes.CM_TYPE)
                            cm2_type = createUnitOnlyType(ModifierTypes.CM2_TYPE)
                            if unitConversionResultsInFloat(
                                cm_type, rhs_type
                            ) or unitConversionResultsInFloat(cm2_type, lhs_type):
                                new_type.builtin = BuiltInTypes.FLOAT_TYPE
                        break

            elif (
                lhs_exclusive == ModifierClass.MASS
                and rhs_exclusive == ModifierClass.ACCELERATION
            ):
                kg_type = createUnitOnlyType(ModifierTypes.KG_TYPE)
                new_type.modifiers.append(ModifierTypes.NEWT_TYPE)
                new_type.exclusive = ExclusiveUnit(
                    unit=ModifierTypes.NEWT_TYPE, unit_class=ModifierClass.FORCE
                )
                if unitConversionResultsInFloat(kg_type, lhs_type):
                    new_type.builtin = BuiltInTypes.FLOAT_TYPE

            elif (
                lhs_exclusive == ModifierClass.ACCELERATION
                and rhs_exclusive == ModifierClass.MASS
            ):
                kg_type = createUnitOnlyType(ModifierTypes.KG_TYPE)
                new_type.modifiers.append(ModifierTypes.NEWT_TYPE)
                new_type.exclusive = ExclusiveUnit(
                    unit=ModifierTypes.NEWT_TYPE, unit_class=ModifierClass.FORCE
                )
                if unitConversionResultsInFloat(kg_type, rhs_type):
                    new_type.builtin = BuiltInTypes.FLOAT_TYPE

            elif lhs_exclusive and not rhs_exclusive:
                for type in modifier_priority_table[lhs_exclusive]:
                    if type in lhs_type.modifiers:
                        new_type.modifiers.append(type)
                        new_type.exclusive = ExclusiveUnit(
                            unit=type, unit_class=lhs_exclusive
                        )
                        break

            elif not lhs_exclusive and rhs_exclusive:
                for type in modifier_priority_table[rhs_exclusive]:
                    if type in rhs_type.modifiers:
                        new_type.modifiers.append(type)
                        new_type.exclusive = ExclusiveUnit(
                            unit=type, unit_class=rhs_exclusive
                        )
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
                    new_type.modifiers.append(ModifierTypes.POSITIVE_TYPE)
                elif (
                    ModifierTypes.NEGATIVE_TYPE in lhs_type.modifiers
                    and ModifierTypes.NEGATIVE_TYPE in rhs_type.modifiers
                ):
                    new_type.modifiers.append(ModifierTypes.POSITIVE_TYPE)
                elif (
                    ModifierTypes.POSITIVE_TYPE in lhs_type.modifiers
                    and ModifierTypes.NEGATIVE_TYPE in rhs_type.modifiers
                ):
                    new_type.modifiers.append(ModifierTypes.NEGATIVE_TYPE)
                elif (
                    ModifierTypes.NEGATIVE_TYPE in lhs_type.modifiers
                    and ModifierTypes.POSITIVE_TYPE in rhs_type.modifiers
                ):
                    new_type.modifiers.append(ModifierTypes.NEGATIVE_TYPE)
            elif ModifierClass.SIGN in lhs_class:
                pass
            elif ModifierClass.SIGN in rhs_class:
                pass

            if (
                ModifierClass.NONZERO in lhs_class
                and ModifierClass.NONZERO in rhs_class
            ):
                new_type.modifiers.append(ModifierTypes.NONZERO_TYPE)
            elif ModifierClass.NONZERO in lhs_class:
                pass
            elif ModifierClass.NONZERO in rhs_class:
                pass

            if ModifierClass.PARITY in lhs_class and ModifierClass.PARITY in rhs_class:
                if (
                    ModifierTypes.EVEN_TYPE in lhs_type.modifiers
                    and ModifierTypes.EVEN_TYPE in rhs_type.modifiers
                ):
                    new_type.modifiers.append(ModifierTypes.EVEN_TYPE)
                elif (
                    ModifierTypes.EVEN_TYPE in lhs_type.modifiers
                    and ModifierTypes.ODD_TYPE in rhs_type.modifiers
                ):
                    new_type.modifiers.append(ModifierTypes.EVEN_TYPE)
                elif (
                    ModifierTypes.ODD_TYPE in lhs_type.modifiers
                    and ModifierTypes.EVEN_TYPE in rhs_type.modifiers
                ):
                    new_type.modifiers.append(ModifierTypes.EVEN_TYPE)
                else:
                    new_type.modifiers.append(ModifierTypes.ODD_TYPE)
            elif ModifierClass.PARITY in lhs_class:
                pass
            elif ModifierClass.PARITY in rhs_class:
                pass
            tree.data.type = new_type
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
                            new_type.builtin = int_type
                            break
            else:
                nonFatalError(
                    f"ERROR: Invalid operands {lhs_type}, {rhs_type} for binary operation"
                )

            lhs_class = getModifierClass(lhs_type.modifiers)
            rhs_class = getModifierClass(rhs_type.modifiers)

            lhs_exclusive = (
                lhs_type.exclusive.unit_class if lhs_type.exclusive else None
            )
            rhs_exclusive = (
                rhs_type.exclusive.unit_class if rhs_type.exclusive else None
            )

            lhs_unit = lhs_type.exclusive.unit if lhs_type.exclusive else None
            rhs_unit = rhs_type.exclusive.unit if rhs_type.exclusive else None

            # EXCLUSIVE CLASS
            if not lhs_exclusive and not rhs_exclusive:
                pass

            elif lhs_exclusive and not rhs_exclusive:
                for type in modifier_priority_table[lhs_exclusive]:
                    if type in lhs_type.modifiers:
                        new_type.modifiers.append(type)
                        new_type.exclusive = ExclusiveUnit(
                            unit=type, unit_class=lhs_exclusive
                        )
                        break

            elif not lhs_exclusive and rhs_exclusive:
                nonFatalError("ERROR: lhs cannot be scalar in division")

            elif (
                lhs_exclusive == ModifierClass.PERCENT
                and rhs_exclusive == ModifierClass.PERCENT
            ):
                for type in modifier_priority_table[lhs_exclusive]:
                    if type in lhs_type.modifiers or type in rhs_type.modifiers:
                        new_type.modifiers.append(type)
                        new_type.exclusive = ExclusiveUnit(
                            unit=type, unit_class=lhs_exclusive
                        )
                        break

            elif lhs_exclusive and rhs_exclusive and lhs_exclusive == rhs_exclusive:
                for type in modifier_priority_table[lhs_exclusive]:
                    if lhs_unit == type or rhs_unit == type:
                        if unitConversionResultsInFloat(
                            createUnitOnlyType(type), lhs_type
                        ) or unitConversionResultsInFloat(
                            createUnitOnlyType(type), rhs_type
                        ):
                            new_type.builtin = BuiltInTypes.FLOAT_TYPE
                            break

            elif (
                lhs_exclusive == ModifierClass.DISTANCE
                and rhs_exclusive == ModifierClass.TIME
            ):
                assert lhs_unit and rhs_unit
                target_velocity = distance_to_velocity[lhs_unit]
                new_type.modifiers.append(target_velocity)
                new_type.exclusive = ExclusiveUnit(
                    unit=target_velocity,
                    unit_class=ModifierClass.VELOCITY,
                )
                if target_velocity == ModifierTypes.MPS_TYPE:
                    if unitConversionResultsInFloat(
                        createUnitOnlyType(ModifierTypes.METER_TYPE), lhs_type
                    ):
                        new_type.builtin = BuiltInTypes.FLOAT_TYPE

                elif target_velocity == ModifierTypes.FPS_TYPE:
                    if unitConversionResultsInFloat(
                        createUnitOnlyType(ModifierTypes.FT_TYPE), lhs_type
                    ):
                        new_type.builtin = BuiltInTypes.FLOAT_TYPE

                if unitConversionResultsInFloat(
                    createUnitOnlyType(ModifierTypes.SECOND_TYPE), rhs_type
                ):
                    new_type.builtin = BuiltInTypes.FLOAT_TYPE

            elif (
                lhs_exclusive == ModifierClass.VELOCITY
                and rhs_exclusive == ModifierClass.TIME
            ):
                new_type.modifiers.append(ModifierTypes.MPS2_TYPE)
                new_type.exclusive = ExclusiveUnit(
                    unit=ModifierTypes.MPS2_TYPE,
                    unit_class=ModifierClass.ACCELERATION,
                )
                if unitConversionResultsInFloat(
                    createUnitOnlyType(ModifierTypes.MPS_TYPE), lhs_type
                ):
                    new_type.builtin = BuiltInTypes.FLOAT_TYPE

                if unitConversionResultsInFloat(
                    createUnitOnlyType(ModifierTypes.SECOND_TYPE), rhs_type
                ):
                    new_type.builtin = BuiltInTypes.FLOAT_TYPE

            elif (
                lhs_exclusive == ModifierClass.FORCE
                and rhs_exclusive == ModifierClass.MASS
            ):
                new_type.modifiers.append(ModifierTypes.MPS2_TYPE)
                new_type.exclusive = ExclusiveUnit(
                    unit=ModifierTypes.MPS2_TYPE,
                    unit_class=ModifierClass.ACCELERATION,
                )
                if unitConversionResultsInFloat(
                    createUnitOnlyType(ModifierTypes.NEWT_TYPE), lhs_type
                ):
                    new_type.builtin = BuiltInTypes.FLOAT_TYPE

                if unitConversionResultsInFloat(
                    createUnitOnlyType(ModifierTypes.KG_TYPE), rhs_type
                ):
                    new_type.builtin = BuiltInTypes.FLOAT_TYPE

            elif (
                lhs_exclusive == ModifierClass.FORCE
                and rhs_exclusive == ModifierClass.ACCELERATION
            ):
                new_type.modifiers.append(ModifierTypes.KG_TYPE)
                new_type.exclusive = ExclusiveUnit(
                    unit=ModifierTypes.KG_TYPE,
                    unit_class=ModifierClass.MASS,
                )
                if unitConversionResultsInFloat(
                    createUnitOnlyType(ModifierTypes.NEWT_TYPE), lhs_type
                ):
                    new_type.builtin = BuiltInTypes.FLOAT_TYPE

                if unitConversionResultsInFloat(
                    createUnitOnlyType(ModifierTypes.MPS2_TYPE), rhs_type
                ):
                    new_type.builtin = BuiltInTypes.FLOAT_TYPE

            elif (
                lhs_exclusive == ModifierClass.VOLUME
                and rhs_exclusive == ModifierClass.AREA
            ):
                for type in modifier_priority_table[lhs_exclusive]:
                    if type in lhs_type.modifiers:
                        distance_type, _ = volume_to_distance_and_area[type]
                        area_type, volume_type = distance_to_area_and_volume[
                            distance_type
                        ]
                        new_type.modifiers.append(distance_type)
                        new_type.exclusive = ExclusiveUnit(
                            unit=distance_type, unit_class=ModifierClass.DISTANCE
                        )
                        if unitConversionResultsInFloat(
                            createUnitOnlyType(volume_type), lhs_type
                        ):
                            new_type.builtin = BuiltInTypes.FLOAT_TYPE
                        if unitConversionResultsInFloat(
                            createUnitOnlyType(area_type), rhs_type
                        ):
                            new_type.builtin = BuiltInTypes.FLOAT_TYPE
                        break

            elif (
                lhs_exclusive == ModifierClass.AREA
                and rhs_exclusive == ModifierClass.DISTANCE
            ):
                for i in range(len(modifier_priority_table[lhs_exclusive])):
                    area_type = modifier_priority_table[lhs_exclusive][i]
                    distance_type = modifier_priority_table[rhs_exclusive][i]
                    if area_type in lhs_type.modifiers:
                        new_type.modifiers.append(area_to_distance[area_type])
                        new_type.exclusive = ExclusiveUnit(
                            unit=area_to_distance[area_type],
                            unit_class=ModifierClass.DISTANCE,
                        )
                        if unitConversionResultsInFloat(
                            createUnitOnlyType(area_to_distance[area_type]), rhs_type
                        ):
                            new_type.builtin = BuiltInTypes.FLOAT_TYPE
                        break
                    elif distance_type in rhs_type.modifiers:
                        new_type.modifiers.append(distance_type)
                        new_type.exclusive = ExclusiveUnit(
                            unit=distance_type,
                            unit_class=ModifierClass.DISTANCE,
                        )
                        if unitConversionResultsInFloat(
                            createUnitOnlyType(distance_type),
                            lhs_type,
                        ):
                            new_type.builtin = BuiltInTypes.FLOAT_TYPE
                        break

            elif (
                lhs_exclusive == ModifierClass.VOLUME
                and rhs_exclusive == ModifierClass.DISTANCE
            ):
                for type in modifier_priority_table[lhs_exclusive]:
                    if type in rhs_type.modifiers:
                        _, area_type = volume_to_distance_and_area[type]
                        distance_type, volume_type = area_to_distance_and_volume[
                            area_type
                        ]
                        new_type.modifiers.append(area_type)
                        new_type.exclusive = ExclusiveUnit(
                            unit=area_type, unit_class=ModifierClass.AREA
                        )
                        if unitConversionResultsInFloat(
                            createUnitOnlyType(volume_type), lhs_type
                        ):
                            new_type.builtin = BuiltInTypes.FLOAT_TYPE
                        if unitConversionResultsInFloat(
                            createUnitOnlyType(distance_type), rhs_type
                        ):
                            new_type.builtin = BuiltInTypes.FLOAT_TYPE
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
                    new_type.modifiers.append(ModifierTypes.POSITIVE_TYPE)
                elif (
                    ModifierTypes.NEGATIVE_TYPE in lhs_type.modifiers
                    and ModifierTypes.NEGATIVE_TYPE in rhs_type.modifiers
                ):
                    new_type.modifiers.append(ModifierTypes.POSITIVE_TYPE)
                elif (
                    ModifierTypes.POSITIVE_TYPE in lhs_type.modifiers
                    and ModifierTypes.NEGATIVE_TYPE in rhs_type.modifiers
                ):
                    new_type.modifiers.append(ModifierTypes.NEGATIVE_TYPE)
                elif (
                    ModifierTypes.NEGATIVE_TYPE in lhs_type.modifiers
                    and ModifierTypes.POSITIVE_TYPE in rhs_type.modifiers
                ):
                    new_type.modifiers.append(ModifierTypes.NEGATIVE_TYPE)
            elif ModifierClass.SIGN in lhs_class:
                pass
            elif ModifierClass.SIGN in rhs_class:
                pass

            if (
                ModifierClass.NONZERO in lhs_class
                and ModifierClass.NONZERO in rhs_class
            ):
                new_type.modifiers.append(ModifierTypes.NONZERO_TYPE)
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
            tree.data.type = new_type
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
                            new_type.builtin = int_type
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
                        new_type.modifiers.append(type)
                        new_type.exclusive = ExclusiveUnit(
                            unit=type, unit_class=lhs_exclusive
                        )
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
                    new_type.modifiers.append(ModifierTypes.EVEN_TYPE)
                elif (
                    ModifierTypes.EVEN_TYPE in lhs_type.modifiers
                    and ModifierTypes.ODD_TYPE in rhs_type.modifiers
                ):
                    pass
                elif (
                    ModifierTypes.ODD_TYPE in lhs_type.modifiers
                    and ModifierTypes.EVEN_TYPE in rhs_type.modifiers
                ):
                    new_type.modifiers.append(ModifierTypes.ODD_TYPE)
                else:
                    pass
            elif ModifierClass.PARITY in lhs_class:
                pass
            elif ModifierClass.PARITY in rhs_class:
                pass
            tree.data.type = new_type
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
                            new_type.builtin = int_type
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
                    new_type.modifiers.append(ModifierTypes.POSITIVE_TYPE)
                elif ModifierTypes.EVEN_TYPE in rhs_type.modifiers:
                    new_type.modifiers.append(ModifierTypes.POSITIVE_TYPE)
                elif ModifierTypes.ODD_TYPE in rhs_type.modifiers:
                    new_type.modifiers.append(ModifierTypes.NEGATIVE_TYPE)
                elif lhs_type.builtin not in int_types:
                    nonFatalError(
                        f"ERROR: negative base for non integer exponent is invalid {lhs_type} and {rhs_type}"
                    )
            elif ModifierClass.SIGN in lhs_class:
                if ModifierTypes.POSITIVE_TYPE in lhs_type.modifiers:
                    new_type.modifiers.append(ModifierTypes.POSITIVE_TYPE)
                elif ModifierTypes.EVEN_TYPE in rhs_type.modifiers:
                    new_type.modifiers.append(ModifierTypes.POSITIVE_TYPE)
                elif ModifierTypes.ODD_TYPE in rhs_type.modifiers:
                    new_type.modifiers.append(ModifierTypes.NEGATIVE_TYPE)
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
                    new_type.modifiers.append(ModifierTypes.NONZERO_TYPE)
            elif ModifierClass.NONZERO in rhs_class:
                pass

            if ModifierClass.PARITY in lhs_class and ModifierClass.PARITY in rhs_class:
                if (
                    ModifierTypes.EVEN_TYPE in lhs_type.modifiers
                    and ModifierTypes.NONZERO_TYPE in rhs_type.modifiers
                    and ModifierTypes.POSITIVE_TYPE in rhs_type.modifiers
                ):
                    new_type.modifiers.append(ModifierTypes.EVEN_TYPE)
                elif (
                    ModifierTypes.ODD_TYPE in lhs_type.modifiers
                    and ModifierTypes.NONZERO_TYPE in rhs_type.modifiers
                    and ModifierTypes.POSITIVE_TYPE in rhs_type.modifiers
                ):
                    new_type.modifiers.append(ModifierTypes.ODD_TYPE)
                else:
                    pass
            elif ModifierClass.PARITY in lhs_class:
                pass
            elif ModifierClass.PARITY in rhs_class:
                pass
            return Type(builtin=new_type.builtin, modifiers=new_type.modifiers)
            tree.data.type = new_type
            return tree.data.type
        elif operator in [
            ASTOperator.NOT_EQUAL_OPERATOR,
            ASTOperator.EQUAL_OPERATOR,
        ]:
            new_type.builtin = BuiltInTypes.BOOL_TYPE
            tree.data.type = new_type
            return tree.data.type
            new_type.builtin = BuiltInTypes.BOOL_TYPE
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

            tree.data.type = new_type
            return tree.data.type
        elif operator in [
            ASTOperator.LESS_OPERATOR,
            ASTOperator.LESS_OR_EQUAL_OPERATOR,
            ASTOperator.GREATER_OPERATOR,
            ASTOperator.GREATER_OR_EQUAL_OPERATOR,
        ]:
            if (
                lhs_type.builtin == BuiltInTypes.STRING_TYPE
                or rhs_type.builtin == BuiltInTypes.STRING_TYPE
            ):
                nonFatalError(
                    f"ERROR: string is invalid for comparison operation {lhs_type} and {rhs_type}"
                )
                return Type(builtin=new_type.builtin)
            elif lhs_type.builtin in num_types or rhs_type.builtin in num_types:
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
                            break
            else:
                nonFatalError(
                    f"ERROR: Invalid operands {lhs_type}, {rhs_type} for binary operation"
                )
            lhs_exclusive = (
                lhs_type.exclusive.unit_class if lhs_type.exclusive else None
            )
            rhs_exclusive = (
                rhs_type.exclusive.unit_class if rhs_type.exclusive else None
            )

            if bool(lhs_exclusive) ^ bool(rhs_exclusive):
                nonFatalError(
                    f"ERROR: mismatched exclusive modifier types {lhs_exclusive} and {rhs_exclusive}"
                )
            elif lhs_exclusive and rhs_exclusive:
                if lhs_exclusive != rhs_exclusive:
                    nonFatalError(
                        f"ERROR: mismatched exclusive modifier types {lhs_type} and {rhs_type}"
                    )
                    return new_type
                assert lhs_type.exclusive and rhs_type.exclusive
                for type in modifier_priority_table[lhs_exclusive]:
                    if (
                        type == lhs_type.exclusive.unit
                        or type == rhs_type.exclusive.unit
                    ):
                        if (
                            lhs_type.exclusive.unit_class == ModifierClass.TEMP
                            and lhs_type.exclusive.unit != rhs_type.exclusive.unit
                        ):
                            nonFatalError(
                                f"ERROR: addition of temperatures must have matching units {lhs_type.exclusive.unit} and {rhs_type.exclusive.unit}"
                            )
                        break
            new_type.builtin = BuiltInTypes.BOOL_TYPE
            tree.data.type = new_type
            return tree.data.type
        elif operator == ASTOperator.AND_OPERATOR:
            new_type.builtin = BuiltInTypes.BOOL_TYPE
            tree.data.type = new_type
            return tree.data.type
        elif operator == ASTOperator.OR_OPERATOR:
            new_type.builtin = BuiltInTypes.BOOL_TYPE
            tree.data.type = new_type
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
            tree.data = pseudo_assignment_op_node.data
            tree.kind = pseudo_assignment_op_node.kind
            tree.token = pseudo_assignment_op_node.token
            tree.data.type = resolveBinaryOp(tree, scope)
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
                            new_type.builtin = int_type
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
                new_type.builtin = BuiltInTypes.FLOAT_TYPE
                tree.data.type = lhs_type
                return tree.data.type
            elif not rhs_exclusive:
                new_type.builtin = BuiltInTypes.FLOAT_TYPE
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
        elif len(modifier_classes) == 1:
            modifier_types = modifier_priority_table[modifier_classes[0]]
            for unit in type.modifiers:
                if unit in modifier_types:
                    type.exclusive = ExclusiveUnit(
                        unit=unit, unit_class=modifier_classes[0]
                    )

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

    assert tree.kind == ASTNodeType.FILE
    for node in tree.data.children:
        if node.kind == ASTNodeType.FUNCTION_STMT:
            resolveFunctionStmt(node, scope)
        elif node.kind == ASTNodeType.DECLARATION:
            resolveDeclaration(node, scope)
    return scope, has_error
