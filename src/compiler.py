from __future__ import annotations
from dataclasses import dataclass
from typing import cast, Union, Literal
from llvmlite import ir
from ast_types import (
    ASTLiteral,
    ASTNode,
    ASTNodeType,
    ASTOperator,
    DeclarationData,
    IdentifierData,
)
from semantic_types import (
    ExclusiveUnit,
    Function,
    ModifierTypes,
    Scope,
    BuiltInTypes,
    ModifierClass,
    Symbol,
    Type,
)
from unit_conversion_table import baked_multiple_conversion_table
from unit_functions import createUnitOnlyType, unitConversionResultsInFloat
from unit_tables import (
    num_types,
    int_types,
    modifier_priority_table,
    multiple_based_units,
    area_to_distance,
    volume_to_distance_and_area,
    distance_to_area_and_volume,
    area_to_distance_and_volume,
    distance_to_area,
)


@dataclass
class BaseConstant:
    pass


@dataclass
class IntConstant(BaseConstant):
    value: int
    type: Literal[BuiltInTypes.INT_TYPE] = BuiltInTypes.INT_TYPE


@dataclass
class FloatConstant(BaseConstant):
    value: float
    type: Literal[BuiltInTypes.FLOAT_TYPE] = BuiltInTypes.FLOAT_TYPE


@dataclass
class CharConstant(BaseConstant):
    value: str
    type: Literal[BuiltInTypes.CHAR_TYPE] = BuiltInTypes.CHAR_TYPE


@dataclass
class StringConstant(BaseConstant):
    value: str
    type: Literal[BuiltInTypes.STRING_TYPE] = BuiltInTypes.STRING_TYPE


@dataclass
class BoolConstant(BaseConstant):
    value: bool
    type: Literal[BuiltInTypes.BOOL_TYPE] = BuiltInTypes.BOOL_TYPE


Constant = Union[IntConstant, FloatConstant, CharConstant, StringConstant, BoolConstant]


def compileFile(tree: ASTNode, code: str, scope: Scope, filename: str, dest_file: str):
    module = ir.Module(name=filename)
    CharType = ir.IntType(8)
    StringType = ir.IntType(8).as_pointer()
    BoolType = ir.IntType(1)
    IntType = ir.IntType(64)
    FloatType = ir.DoubleType()
    VoidType = ir.VoidType()
    Zero = ir.Constant(IntType, 0)
    One = ir.Constant(IntType, 1)
    ZeroFloat = ir.Constant(FloatType, 0.0)
    PercentScale = ir.Constant(FloatType, 0.01)
    str_counter = 0

    def compileStatement(
        tree: ASTNode, scope: Scope, builder: ir.IRBuilder, alloca_block: ir.Block
    ):
        if tree.kind == ASTNodeType.DECLARATION:
            compileDeclaration(tree, scope, builder, alloca_block)
        elif tree.kind == ASTNodeType.IF_STMT:
            compileIfStmt(tree, scope, builder, alloca_block)
        elif tree.kind == ASTNodeType.SWITCH_STMT:
            compileSwitchStmt(tree, scope, builder, alloca_block)
        elif tree.kind == ASTNodeType.SWEEP_STMT:
            compileSweepStmt(tree, scope, builder, alloca_block)
        elif tree.kind == ASTNodeType.WHILE_STMT:
            compileWhileStmt(tree, scope, builder, alloca_block)
        elif tree.kind == ASTNodeType.FUNCTION_STMT:
            print(
                "WARN: function declaration inside function ignored, not yet implemented"
            )
            # compileFunctionStmt(tree, scope, builder)
        elif tree.kind == ASTNodeType.FOR_STMT:
            compileForStmt(tree, scope, builder, alloca_block)
        elif tree.kind == ASTNodeType.BLOCK:
            compileBlock(tree, scope, builder, alloca_block)
        elif tree.kind == ASTNodeType.NEXT_STMT:
            compileNextStmt(tree, scope, builder, alloca_block)
        elif tree.kind == ASTNodeType.STOP_STMT:
            compileStopStmt(tree, scope, builder, alloca_block)
        elif tree.kind == ASTNodeType.RETURN_STMT:
            compileReturnStmt(tree, scope, builder, alloca_block)
        else:
            compileExpression(tree, scope, builder)

    def compileIfStmt(
        tree: ASTNode, scope: Scope, builder: ir.IRBuilder, alloca_block: ir.Block
    ):
        then_block = builder.append_basic_block("then")
        ifnot_block = builder.append_basic_block("ifnot")
        merge_block = builder.append_basic_block("merge")

        expr_cmp = compileExpression(tree.data.expr, scope, builder)
        if isinstance(expr_cmp, BaseConstant):
            expr_cmp = constantToIrConstant(expr_cmp, tree.data.expr.data.type)
        expr_cmp = toBool(expr_cmp, tree.data.expr.data.type, builder)
        builder.cbranch(expr_cmp, truebr=then_block, falsebr=ifnot_block)
        builder.position_at_end(then_block)
        compileBlock(tree.data.block, scope, builder, alloca_block)
        assert builder.block
        if not builder.block.is_terminated:
            builder.branch(merge_block)

        for i, (expr, block) in enumerate(tree.data.elif_stmts):
            builder.position_at_end(ifnot_block)

            elif_then = builder.append_basic_block(f"then{i}")
            new_ifnot_block = builder.append_basic_block(f"ifnot{i}")
            expr_cmp = compileExpression(expr, scope, builder)
            if isinstance(expr_cmp, BaseConstant):
                expr_cmp = constantToIrConstant(expr_cmp, expr.data.type)
            expr_cmp = toBool(expr_cmp, expr.data.type, builder)
            builder.cbranch(expr_cmp, truebr=elif_then, falsebr=new_ifnot_block)

            builder.position_at_end(elif_then)
            compileBlock(block, scope, builder, alloca_block)
            assert builder.block
            if not builder.block.is_terminated:
                builder.branch(merge_block)

            ifnot_block = new_ifnot_block

        if tree.data.else_stmt:
            builder.position_at_end(ifnot_block)
            compileBlock(tree.data.else_stmt, scope, builder, alloca_block)
            assert builder.block
            if not builder.block.is_terminated:
                builder.branch(merge_block)
        else:
            builder.position_at_end(ifnot_block)
            assert builder.block
            if not builder.block.is_terminated:
                builder.branch(merge_block)
        builder.position_at_end(merge_block)

    def compileSwitchStmt(
        tree: ASTNode, scope: Scope, builder: ir.IRBuilder, alloca_block: ir.Block
    ):
        expr_cmp = compileExpression(tree.data.expr, scope, builder)
        if isinstance(expr_cmp, BaseConstant):
            expr_cmp = constantToIrConstant(expr_cmp, tree.data.expr.data.type)

        if len(tree.data.case_stmts) == 0:
            assert tree.data.default_stmt
            compileStatement(tree.data.default_stmt, scope, builder, alloca_block)
            return

        n = len(tree.data.case_stmts)
        assert n >= 1
        case_blocks = [builder.append_basic_block(f"case{i}") for i in range(n)]
        notcase_blocks = [builder.append_basic_block(f"notcase{i}") for i in range(n)]
        merge_block = builder.append_basic_block("merge")
        tree.data.merge = merge_block

        default_block = merge_block

        if tree.data.default_stmt:
            default_block = builder.append_basic_block("default")

        builder.branch(notcase_blocks[0])

        for i, (case_expr, case_node) in enumerate(tree.data.case_stmts):
            builder.position_at_end(notcase_blocks[i])
            case_cmp = compileExpression(case_expr, scope, builder)
            if isinstance(case_cmp, BaseConstant):
                case_cmp = constantToIrConstant(case_cmp, case_expr.data.type)
            result_cmp = builder.icmp_signed("==", expr_cmp, case_cmp)
            notcase_target = notcase_blocks[i + 1] if i + 1 < n else default_block
            builder.cbranch(result_cmp, truebr=case_blocks[i], falsebr=notcase_target)

            builder.position_at_end(case_blocks[i])
            compileStatement(case_node, scope, builder, alloca_block)
            assert builder.block
            if not builder.block.is_terminated:
                if i + 1 < n:
                    builder.branch(case_blocks[i + 1])
                else:
                    builder.branch(default_block)

        if tree.data.default_stmt:
            builder.position_at_end(default_block)
            compileStatement(tree.data.default_stmt, scope, builder, alloca_block)
            assert builder.block
            if not builder.block.is_terminated:
                builder.branch(merge_block)
        builder.position_at_end(merge_block)

    def compileSweepStmt(
        tree: ASTNode, scope: Scope, builder: ir.IRBuilder, alloca_block: ir.Block
    ):
        expr_cmp = compileExpression(tree.data.expr, scope, builder)
        if isinstance(expr_cmp, BaseConstant):
            expr_cmp = constantToIrConstant(expr_cmp, tree.data.expr.data.type)

        if len(tree.data.range_stmts) == 0:
            assert tree.data.default_stmt
            compileStatement(tree.data.default_stmt, scope, builder, alloca_block)
            return

        n = len(tree.data.range_stmts)
        assert n >= 1
        range_blocks = [builder.append_basic_block(f"range{i}") for i in range(n)]
        notrange_blocks = [builder.append_basic_block(f"notrange{i}") for i in range(n)]
        merge_block = builder.append_basic_block("merge")
        tree.data.merge = merge_block

        default_block = merge_block

        if tree.data.default_stmt:
            default_block = builder.append_basic_block("default")

        builder.branch(notrange_blocks[0])

        for i, (range_expr, range_node) in enumerate(tree.data.range_stmts):
            builder.position_at_end(notrange_blocks[i])
            range_cmp = compileExpression(range_expr, scope, builder)
            if isinstance(range_cmp, BaseConstant):
                range_cmp = constantToIrConstant(range_cmp, range_expr.data.type)
            if i == n - 1:
                result_cmp = builder.icmp_signed("==", expr_cmp, range_cmp)
            else:
                greater_expr, _ = tree.data.range_stmts[i + 1]
                greater_cmp = compileExpression(greater_expr, scope, builder)
                if isinstance(greater_cmp, BaseConstant):
                    greater_cmp = constantToIrConstant(
                        greater_cmp, greater_expr.data.type
                    )
                greater_cmp = builder.icmp_signed("<", expr_cmp, greater_cmp)
                less_or_eq_cmp = builder.icmp_signed(">=", expr_cmp, range_cmp)

                result_cmp = builder.and_(less_or_eq_cmp, greater_cmp)

            notrange_target = notrange_blocks[i + 1] if i + 1 < n else default_block
            builder.cbranch(result_cmp, truebr=range_blocks[i], falsebr=notrange_target)

            builder.position_at_end(range_blocks[i])
            compileStatement(range_node, scope, builder, alloca_block)
            assert builder.block
            if not builder.block.is_terminated:
                if i + 1 < n:
                    builder.branch(range_blocks[i + 1])
                else:
                    builder.branch(default_block)

        if tree.data.default_stmt:
            builder.position_at_end(default_block)
            compileStatement(tree.data.default_stmt, scope, builder, alloca_block)
            assert builder.block
            if not builder.block.is_terminated:
                builder.branch(merge_block)
        builder.position_at_end(merge_block)

    def compileWhileStmt(
        tree: ASTNode, scope: Scope, builder: ir.IRBuilder, alloca_block: ir.Block
    ):
        cond_block = builder.append_basic_block("while_cond")
        body_block = builder.append_basic_block("while_body")
        merge_block = builder.append_basic_block("while_merge")
        tree.data.merge = merge_block
        tree.data.cond = cond_block
        if tree.data.right_expr:
            right_expr = compileExpression(tree.data.right_expr, scope, builder)
            if isinstance(right_expr, BaseConstant):
                right_expr = constantToIrConstant(
                    right_expr, tree.data.right_expr.data.type
                )
            right_expr = toBool(right_expr, tree.data.right_expr.data.type, builder)
            builder.cbranch(right_expr, body_block, cond_block)
        else:
            builder.branch(cond_block)
        builder.position_at_end(cond_block)
        left_expr = compileExpression(tree.data.left_expr, scope, builder)
        if isinstance(left_expr, BaseConstant):
            left_expr = constantToIrConstant(left_expr, tree.data.left_expr.data.type)
        left_expr = toBool(left_expr, tree.data.left_expr.data.type, builder)
        builder.cbranch(left_expr, body_block, merge_block)
        builder.position_at_end(body_block)
        compileBlock(tree.data.block, scope, builder, alloca_block)
        assert builder.block
        if not builder.block.is_terminated:
            builder.branch(cond_block)
        builder.position_at_end(merge_block)

    def compileForStmt(
        tree: ASTNode, scope: Scope, builder: ir.IRBuilder, alloca_block: ir.Block
    ):
        assert tree.scope
        new_scope = tree.scope
        init_block = builder.append_basic_block("for_init")
        cond_block = builder.append_basic_block("for_cond")
        body_block = builder.append_basic_block("for_body")
        merge_block = builder.append_basic_block("for_merge")
        tree.data.merge = merge_block
        tree.data.cond = cond_block
        builder.branch(init_block)
        builder.position_at_end(init_block)
        if tree.data.init:
            if tree.data.init.kind == ASTNodeType.DECLARATION:
                compileDeclaration(tree.data.init, new_scope, builder, alloca_block)
            else:
                compileExpression(tree.data.init, new_scope, builder)
        builder.branch(cond_block)
        builder.position_at_end(cond_block)
        if tree.data.condition:
            expr = compileExpression(tree.data.condition, new_scope, builder)
            if isinstance(expr, BaseConstant):
                expr = constantToIrConstant(expr, tree.data.condition.data.type)
            expr = toBool(expr, tree.data.condition.data.type, builder)
            builder.cbranch(expr, body_block, merge_block)
        else:
            builder.branch(body_block)

        builder.position_at_end(body_block)
        compileBlock(tree.data.block, new_scope, builder, alloca_block)

        assert builder.block
        if not builder.block.is_terminated:
            if tree.data.update:
                compileExpression(tree.data.update, new_scope, builder)
            builder.branch(cond_block)

        builder.position_at_end(merge_block)

    def compileBlock(
        tree: ASTNode, scope: Scope, builder: ir.IRBuilder, alloca_block: ir.Block
    ):
        block_scope = tree.scope
        assert block_scope

        for node in tree.data.statements:
            assert builder.block
            if builder.block.is_terminated:
                break
            compileStatement(node, block_scope, builder, alloca_block)

    def compileFunctionBlock(
        tree: ASTNode, scope: Scope, builder: ir.IRBuilder, alloca_block: ir.Block
    ):
        for node in tree.data.statements:
            assert builder.block
            if builder.block.is_terminated:
                break
            compileStatement(node, scope, builder, alloca_block)

    def compileNextStmt(
        tree: ASTNode, scope: Scope, builder: ir.IRBuilder, alloca_block: ir.Block
    ):
        if tree.data.target.kind in [ASTNodeType.FOR_STMT, ASTNodeType.WHILE_STMT]:
            assert tree.data.target.data.cond
            builder.branch(tree.data.target.data.cond)

    def compileStopStmt(
        tree: ASTNode, scope: Scope, builder: ir.IRBuilder, alloca_block: ir.Block
    ):
        if tree.data.target.kind in [
            ASTNodeType.SWITCH_STMT,
            ASTNodeType.SWEEP_STMT,
            ASTNodeType.FOR_STMT,
            ASTNodeType.WHILE_STMT,
        ]:
            assert tree.data.target.data.merge
            builder.branch(tree.data.target.data.merge)

    def compileReturnStmt(
        tree: ASTNode, scope: Scope, builder: ir.IRBuilder, alloca_block: ir.Block
    ):
        expr = None
        func_data = tree.data.target.data

        if tree.data.expression:
            expr = compileExpression(tree.data.expression, scope, builder)
            if isinstance(expr, BaseConstant):
                expr = constantToIrConstant(expr, tree.data.expression.data.type)
            expr = castType(
                expr, func_data.return_type, tree.data.expression.data.type, builder
            )
            builder.ret(expr)
        else:
            builder.ret_void()

    def compileFunctionStmt(
        tree: ASTNode,
        scope: Scope,
        builder: ir.IRBuilder,
    ):
        func_scope = tree.scope
        assert func_scope

        func_name = compileIdentifier(tree.data.name)
        func = reference(scope, func_name)
        assert isinstance(func.type, Function)

        func_type: Function = func.type
        params = func_type.parameters
        params_type = [typeToIrType(param.type) for param in params]
        return_type = typeToIrType(func_type.return_type)

        func_ir_type = ir.FunctionType(return_type, params_type)
        func_ir = ir.Function(module, func_ir_type, name=func_name)
        func.type.func_ir = func_ir
        alloca_block = func_ir.append_basic_block("alloca")
        new_builder = ir.IRBuilder(alloca_block)

        for arg, param in zip(func_ir.args, func_type.parameters):
            arg.name = param.name
            alloca = new_builder.alloca(arg.type, name=param.name)
            new_builder.store(arg, alloca)
            symbol = reference(func_scope, param.name)
            symbol.ptr = alloca

        entry_block = new_builder.append_basic_block("entry")
        new_builder.branch(entry_block)
        new_builder.position_at_end(entry_block)

        compileFunctionBlock(tree.data.block, func_scope, new_builder, alloca_block)

        assert new_builder.block
        if not new_builder.block.is_terminated:
            if func_type.return_type.builtin == BuiltInTypes.VOID_TYPE:
                new_builder.ret_void()
            elif func_type.return_type.builtin == BuiltInTypes.STRING_TYPE:
                new_builder.ret(ir.Constant(ir.PointerType(ir.IntType(8)), None))
            else:
                new_builder.ret(ir.Constant(typeToIrType(func_type.return_type), 0))

    def compileDeclaration(
        tree: ASTNode,
        scope: Scope,
        builder: ir.IRBuilder,
        alloca_block: ir.Block | None,
    ):
        data: DeclarationData = tree.data
        name_data: IdentifierData = data.name.data

        assert name_data.symbol
        assert isinstance(name_data.symbol.type, Type)
        new_type = typeToIrType(name_data.symbol.type)
        name = compileIdentifier(data.name)
        if name_data.symbol.scope.parent_scope is None:
            global_var = ir.GlobalVariable(module, new_type, name=name)
            global_var.linkage = "internal"
            if tree.data.expression:
                constant_expr = compileExpression(tree.data.expression, scope, builder)
                assert isinstance(constant_expr, BaseConstant)
                global_var.initializer = constantToIrConstant(  # type: ignore
                    constant_expr, name_data.symbol.type
                )
            name_data.symbol.ptr = global_var
            return
        current_block = builder.block
        assert alloca_block
        builder.position_at_start(alloca_block)
        alloca = builder.alloca(new_type, name=name)
        builder.position_at_end(current_block)

        if tree.data.expression:
            expr = compileExpression(tree.data.expression, scope, builder)
            if isinstance(expr, BaseConstant):
                expr = constantToIrConstant(expr, tree.data.expression.data.type)

            if tree.data.expression.data.type.exclusive:
                expr = convertToUnit(
                    expr, name_data.symbol.type, tree.data.expression.data.type, builder
                )
                if unitConversionResultsInFloat(
                    name_data.symbol.type, tree.data.expression.data.type
                ):
                    tree.data.expression.data.type.builtin = BuiltInTypes.FLOAT_TYPE

            expr = castType(
                expr, name_data.symbol.type, tree.data.expression.data.type, builder
            )

            builder.store(expr, alloca)
        name_data.symbol.ptr = alloca

    def compileIdentifier(tree: ASTNode):
        return code[tree.token.start : tree.token.end]

    def compileExpression(
        tree: ASTNode, scope: Scope, builder: ir.IRBuilder
    ) -> Constant | ir.Value:
        # if tree.kind == ASTNodeType.BINARY_OP:
        #     return compileBinaryOp(tree)
        if tree.kind == ASTNodeType.UNARY_OP:
            return compileUnaryOp(tree, scope, builder)
        elif tree.kind == ASTNodeType.FUNCTION_CALL:
            return compileFunctionCall(tree, scope, builder)
        # elif tree.kind == ASTNodeType.ARRAY_INDEX:
        #     return compileArrayIndex(tree)
        elif tree.kind == ASTNodeType.LITERAL:
            return compileLiteral(tree)
        elif tree.kind == ASTNodeType.IDENTIFIER:
            symbol = compileSymbol(tree, scope)
            assert symbol.ptr
            return builder.load(symbol.ptr)
        assert False

    def compileBinaryOp(
        tree: ASTNode, scope: Scope, builder: ir.IRBuilder
    ) -> ir.Value | Constant:
        lhs = tree.data.lhs
        rhs = tree.data.rhs
        lhs_type: Type = lhs.data.type
        rhs_type: Type = rhs.data.type
        result_type: Type = tree.data.type
        lhs_value = compileExpression(lhs, scope, builder)
        rhs_value = compileExpression(rhs, scope, builder)
        operator = tree.data.operator

        if operator == ASTOperator.ADD_OPERATOR:
            if (
                lhs_type.builtin == BuiltInTypes.STRING_TYPE
                and rhs_type.builtin == BuiltInTypes.STRING_TYPE
            ):
                print("WARN: string + concatenation not implemented yet")
            elif lhs_type.builtin in num_types and rhs_type.builtin in num_types:
                lhs_value = castType(lhs_value, result_type, lhs_type, builder)
                rhs_value = castType(rhs_value, result_type, rhs_type, builder)

            exclusive_class = (
                result_type.exclusive.unit_class if result_type.exclusive else None
            )
            if not exclusive_class:
                if result_type.builtin == BuiltInTypes.FLOAT_TYPE:
                    return cast(ir.Value, builder.fadd(lhs_value, rhs_value))
                else:
                    return cast(ir.Value, builder.add(lhs_value, rhs_value))

            unit_types = modifier_priority_table[exclusive_class]
            target_unit = list(filter(lambda x: x in unit_types, result_type.modifiers))
            target_unit_type = Type(
                builtin=result_type.builtin,
                modifiers=target_unit,
                exclusive=ExclusiveUnit(
                    unit=target_unit[0], unit_class=exclusive_class
                ),
            )

            if lhs_type.exclusive and rhs_type.exclusive:
                lhs_value = convertToUnit(
                    lhs_value, target_unit_type, lhs_type, builder
                )
                rhs_value = convertToUnit(
                    rhs_value, target_unit_type, rhs_type, builder
                )

            if result_type.builtin == BuiltInTypes.FLOAT_TYPE:
                return cast(ir.Value, builder.fadd(lhs_value, rhs_value))
            else:
                return cast(ir.Value, builder.add(lhs_value, rhs_value))

        elif operator == ASTOperator.SUB_OPERATOR:
            if lhs_type.builtin in num_types and rhs_type.builtin in num_types:
                lhs_value = castType(lhs_value, result_type, lhs_type, builder)
                rhs_value = castType(rhs_value, result_type, rhs_type, builder)
            exclusive_class = (
                result_type.exclusive.unit_class if result_type.exclusive else None
            )
            if not exclusive_class:
                if result_type.builtin == BuiltInTypes.FLOAT_TYPE:
                    return cast(ir.Value, builder.fsub(lhs_value, rhs_value))
                else:
                    return cast(ir.Value, builder.sub(lhs_value, rhs_value))

            unit_types = modifier_priority_table[exclusive_class]
            target_unit = list(filter(lambda x: x in unit_types, result_type.modifiers))
            target_unit_type = Type(
                builtin=result_type.builtin,
                modifiers=target_unit,
                exclusive=ExclusiveUnit(
                    unit=target_unit[0], unit_class=exclusive_class
                ),
            )

            if lhs_type.exclusive and rhs_type.exclusive:
                lhs_value = convertToUnit(
                    lhs_value, target_unit_type, lhs_type, builder
                )
                rhs_value = convertToUnit(
                    rhs_value, target_unit_type, rhs_type, builder
                )

            if result_type.builtin == BuiltInTypes.FLOAT_TYPE:
                return cast(ir.Value, builder.fsub(lhs_value, rhs_value))
            else:
                return cast(ir.Value, builder.sub(lhs_value, rhs_value))

        elif operator == ASTOperator.MULT_OPERATOR:
            if lhs_type.builtin in num_types and rhs_type.builtin in num_types:
                lhs_value = castType(lhs_value, result_type, lhs_type, builder)
                rhs_value = castType(rhs_value, result_type, rhs_type, builder)
            lhs_exclusive = (
                lhs_type.exclusive.unit_class if lhs_type.exclusive else None
            )
            lhs_unit = lhs_type.exclusive.unit if lhs_type.exclusive else None
            rhs_exclusive = (
                rhs_type.exclusive.unit_class if rhs_type.exclusive else None
            )
            rhs_unit = rhs_type.exclusive.unit if rhs_type.exclusive else None
            exclusive_class = (
                result_type.exclusive.unit_class if result_type.exclusive else None
            )
            exclusive_unit = (
                result_type.exclusive.unit if result_type.exclusive else None
            )

            if (
                not exclusive_class
                and lhs_exclusive != ModifierClass.PERCENT
                and rhs_exclusive != ModifierClass.PERCENT
            ):
                if result_type.builtin == BuiltInTypes.FLOAT_TYPE:
                    return cast(ir.Value, builder.fmul(lhs_value, rhs_value))
                else:
                    return cast(ir.Value, builder.mul(lhs_value, rhs_value))

            elif (
                lhs_exclusive == ModifierClass.VELOCITY
                and rhs_exclusive == ModifierClass.TIME
            ):
                if lhs_unit == ModifierTypes.MPS_TYPE:
                    rhs_value = convertToUnit(
                        rhs_value,
                        createUnitOnlyType(ModifierTypes.SECOND_TYPE),
                        rhs_type,
                        builder,
                    )
                elif lhs_unit == ModifierTypes.FPS_TYPE:
                    rhs_value = convertToUnit(
                        rhs_value,
                        createUnitOnlyType(ModifierTypes.SECOND_TYPE),
                        rhs_type,
                        builder,
                    )
            elif (
                lhs_exclusive == ModifierClass.TIME
                and rhs_exclusive == ModifierClass.VELOCITY
            ):
                if rhs_unit == ModifierTypes.MPS_TYPE:
                    lhs_value = convertToUnit(
                        lhs_value,
                        createUnitOnlyType(ModifierTypes.SECOND_TYPE),
                        lhs_type,
                        builder,
                    )
                elif rhs_unit == ModifierTypes.FPS_TYPE:
                    lhs_value = convertToUnit(
                        lhs_value,
                        createUnitOnlyType(ModifierTypes.SECOND_TYPE),
                        lhs_type,
                        builder,
                    )

            elif (
                lhs_exclusive == ModifierClass.ACCELERATION
                and rhs_exclusive == ModifierClass.TIME
            ):
                if lhs_unit == ModifierTypes.MPS2_TYPE:
                    rhs_value = convertToUnit(
                        rhs_value,
                        createUnitOnlyType(ModifierTypes.SECOND_TYPE),
                        rhs_type,
                        builder,
                    )
            elif (
                lhs_exclusive == ModifierClass.TIME
                and rhs_exclusive == ModifierClass.ACCELERATION
            ):
                if rhs_unit == ModifierTypes.MPS2_TYPE:
                    lhs_value = convertToUnit(
                        lhs_value,
                        createUnitOnlyType(ModifierTypes.SECOND_TYPE),
                        lhs_type,
                        builder,
                    )

            elif (
                lhs_exclusive == ModifierClass.PERCENT
                and rhs_exclusive == ModifierClass.PERCENT
            ):
                pass
            elif (
                lhs_exclusive != ModifierClass.PERCENT
                and rhs_exclusive == ModifierClass.PERCENT
            ):
                rhs_value = cast(
                    ir.Value,
                    builder.fmul(rhs_value, PercentScale),
                )
            elif (
                lhs_exclusive == ModifierClass.PERCENT
                and rhs_exclusive != ModifierClass.PERCENT
            ):
                lhs_value = cast(
                    ir.Value,
                    builder.fmul(lhs_value, PercentScale),
                )

            elif (
                lhs_exclusive == ModifierClass.DISTANCE
                and rhs_exclusive == ModifierClass.DISTANCE
            ):
                assert exclusive_unit
                distance_type = area_to_distance[exclusive_unit]
                lhs_value = convertToUnit(
                    lhs_value, createUnitOnlyType(distance_type), lhs_type, builder
                )
                rhs_value = convertToUnit(
                    rhs_value, createUnitOnlyType(distance_type), rhs_type, builder
                )

            elif (
                lhs_exclusive == ModifierClass.DISTANCE
                and rhs_exclusive == ModifierClass.AREA
            ):
                assert exclusive_unit
                distance_type, area_type = volume_to_distance_and_area[exclusive_unit]
                lhs_value = convertToUnit(
                    lhs_value, createUnitOnlyType(distance_type), lhs_type, builder
                )
                rhs_value = convertToUnit(
                    rhs_value, createUnitOnlyType(area_type), rhs_type, builder
                )
            elif (
                lhs_exclusive == ModifierClass.AREA
                and rhs_exclusive == ModifierClass.DISTANCE
            ):
                assert exclusive_unit
                distance_type, area_type = volume_to_distance_and_area[exclusive_unit]
                lhs_value = convertToUnit(
                    lhs_value, createUnitOnlyType(area_type), lhs_type, builder
                )
                rhs_value = convertToUnit(
                    rhs_value, createUnitOnlyType(distance_type), rhs_type, builder
                )

            elif (
                lhs_exclusive == ModifierClass.MASS
                and rhs_exclusive == ModifierClass.ACCELERATION
            ):
                lhs_value = convertToUnit(
                    lhs_value,
                    createUnitOnlyType(ModifierTypes.KG_TYPE),
                    lhs_type,
                    builder,
                )
                rhs_value = convertToUnit(
                    rhs_value,
                    createUnitOnlyType(ModifierTypes.MPS2_TYPE),
                    rhs_type,
                    builder,
                )
            elif (
                lhs_exclusive == ModifierClass.ACCELERATION
                and rhs_exclusive == ModifierClass.MASS
            ):
                lhs_value = convertToUnit(
                    lhs_value,
                    createUnitOnlyType(ModifierTypes.MPS2_TYPE),
                    lhs_type,
                    builder,
                )
                rhs_value = convertToUnit(
                    rhs_value,
                    createUnitOnlyType(ModifierTypes.KG_TYPE),
                    rhs_type,
                    builder,
                )

            if result_type.builtin == BuiltInTypes.FLOAT_TYPE:
                return cast(ir.Value, builder.fmul(lhs_value, rhs_value))
            else:
                return cast(ir.Value, builder.mul(lhs_value, rhs_value))

        elif operator == ASTOperator.DIV_OPERATOR:
            if lhs_type.builtin in num_types and rhs_type.builtin in num_types:
                lhs_value = castType(lhs_value, result_type, lhs_type, builder)
                rhs_value = castType(rhs_value, result_type, rhs_type, builder)
            lhs_exclusive = (
                lhs_type.exclusive.unit_class if lhs_type.exclusive else None
            )
            lhs_unit = lhs_type.exclusive.unit if lhs_type.exclusive else None
            rhs_exclusive = (
                rhs_type.exclusive.unit_class if rhs_type.exclusive else None
            )
            rhs_unit = rhs_type.exclusive.unit if rhs_type.exclusive else None
            exclusive_class = (
                result_type.exclusive.unit_class if result_type.exclusive else None
            )
            exclusive_unit = (
                result_type.exclusive.unit if result_type.exclusive else None
            )

            if lhs_exclusive and not rhs_exclusive:
                pass

            elif (
                lhs_exclusive == ModifierClass.PERCENT
                and rhs_exclusive == ModifierClass.PERCENT
            ):
                pass

            elif lhs_exclusive and rhs_exclusive and lhs_exclusive == rhs_exclusive:
                for type in modifier_priority_table[lhs_exclusive]:
                    if lhs_unit == type or rhs_unit == type:
                        lhs_value = convertToUnit(
                            lhs_value, createUnitOnlyType(type), lhs_type, builder
                        )
                        rhs_value = convertToUnit(
                            rhs_value, createUnitOnlyType(type), rhs_type, builder
                        )
                        break

            elif (
                lhs_exclusive == ModifierClass.DISTANCE
                and rhs_exclusive == ModifierClass.TIME
            ):
                assert lhs_unit and rhs_unit and exclusive_unit
                target_velocity = exclusive_unit
                if target_velocity == ModifierTypes.MPS_TYPE:
                    lhs_value = convertToUnit(
                        lhs_value,
                        createUnitOnlyType(ModifierTypes.METER_TYPE),
                        lhs_type,
                        builder,
                    )

                elif target_velocity == ModifierTypes.FPS_TYPE:
                    lhs_value = convertToUnit(
                        lhs_value,
                        createUnitOnlyType(ModifierTypes.FT_TYPE),
                        lhs_type,
                        builder,
                    )

                rhs_value = convertToUnit(
                    rhs_value,
                    createUnitOnlyType(ModifierTypes.SECOND_TYPE),
                    rhs_type,
                    builder,
                )

            elif (
                lhs_exclusive == ModifierClass.VELOCITY
                and rhs_exclusive == ModifierClass.TIME
            ):
                lhs_value = convertToUnit(
                    lhs_value,
                    createUnitOnlyType(ModifierTypes.MPS_TYPE),
                    lhs_type,
                    builder,
                )
                rhs_value = convertToUnit(
                    rhs_value,
                    createUnitOnlyType(ModifierTypes.SECOND_TYPE),
                    rhs_type,
                    builder,
                )

            elif (
                lhs_exclusive == ModifierClass.FORCE
                and rhs_exclusive == ModifierClass.MASS
            ):
                lhs_value = convertToUnit(
                    lhs_value,
                    createUnitOnlyType(ModifierTypes.NEWT_TYPE),
                    lhs_type,
                    builder,
                )
                rhs_value = convertToUnit(
                    rhs_value,
                    createUnitOnlyType(ModifierTypes.KG_TYPE),
                    rhs_type,
                    builder,
                )

            elif (
                lhs_exclusive == ModifierClass.FORCE
                and rhs_exclusive == ModifierClass.ACCELERATION
            ):
                lhs_value = convertToUnit(
                    lhs_value,
                    createUnitOnlyType(ModifierTypes.NEWT_TYPE),
                    lhs_type,
                    builder,
                )
                rhs_value = convertToUnit(
                    rhs_value,
                    createUnitOnlyType(ModifierTypes.MPS2_TYPE),
                    rhs_type,
                    builder,
                )

            elif (
                lhs_exclusive == ModifierClass.VOLUME
                and rhs_exclusive == ModifierClass.AREA
            ):
                assert exclusive_unit
                area_type, volume_type = distance_to_area_and_volume[exclusive_unit]
                lhs_value = convertToUnit(
                    lhs_value, createUnitOnlyType(volume_type), lhs_type, builder
                )
                rhs_value = convertToUnit(
                    rhs_value, createUnitOnlyType(area_type), rhs_type, builder
                )

            elif (
                lhs_exclusive == ModifierClass.AREA
                and rhs_exclusive == ModifierClass.DISTANCE
            ):
                assert exclusive_unit
                area_type = distance_to_area[exclusive_unit]
                distance_type = exclusive_unit
                lhs_value = convertToUnit(
                    lhs_value, createUnitOnlyType(area_type), lhs_type, builder
                )
                rhs_value = convertToUnit(
                    rhs_value, createUnitOnlyType(distance_type), rhs_type, builder
                )

            elif (
                lhs_exclusive == ModifierClass.VOLUME
                and rhs_exclusive == ModifierClass.DISTANCE
            ):
                assert exclusive_unit
                distance_type, volume_type = area_to_distance_and_volume[exclusive_unit]
                lhs_value = convertToUnit(
                    lhs_value, createUnitOnlyType(volume_type), lhs_type, builder
                )
                rhs_value = convertToUnit(
                    rhs_value, createUnitOnlyType(distance_type), rhs_type, builder
                )

            if result_type.builtin == BuiltInTypes.FLOAT_TYPE:
                return cast(ir.Value, builder.fdiv(lhs_value, rhs_value))
            else:
                return cast(ir.Value, builder.sdiv(lhs_value, rhs_value))

        elif operator == ASTOperator.MOD_OPERATOR:
            if lhs_type.builtin in num_types and rhs_type.builtin in num_types:
                lhs_value = castType(lhs_value, result_type, lhs_type, builder)
                rhs_value = castType(rhs_value, result_type, rhs_type, builder)

            exclusive_class = (
                result_type.exclusive.unit_class if result_type.exclusive else None
            )
            if not exclusive_class:
                if result_type.builtin == BuiltInTypes.FLOAT_TYPE:
                    return cast(ir.Value, builder.fadd(lhs_value, rhs_value))
                else:
                    return cast(ir.Value, builder.add(lhs_value, rhs_value))

            unit_types = modifier_priority_table[exclusive_class]
            target_unit = list(filter(lambda x: x in unit_types, result_type.modifiers))
            target_unit_type = Type(
                builtin=result_type.builtin,
                modifiers=target_unit,
                exclusive=ExclusiveUnit(
                    unit=target_unit[0], unit_class=exclusive_class
                ),
            )

            if lhs_type.exclusive and rhs_type.exclusive:
                lhs_value = convertToUnit(
                    lhs_value, target_unit_type, lhs_type, builder
                )
                rhs_value = convertToUnit(
                    rhs_value, target_unit_type, rhs_type, builder
                )

            if result_type.builtin == BuiltInTypes.FLOAT_TYPE:
                return cast(ir.Value, builder.frem(lhs_value, rhs_value))
            else:
                return cast(ir.Value, builder.srem(lhs_value, rhs_value))

        elif operator == ASTOperator.EXP_OPERATOR:
            if lhs_type.builtin in num_types and rhs_type.builtin in num_types:
                lhs_value = castType(lhs_value, result_type, lhs_type, builder)
                rhs_value = castType(rhs_value, result_type, rhs_type, builder)
            exclusive_class = (
                result_type.exclusive.unit_class if result_type.exclusive else None
            )
            if not exclusive_class:
                if result_type.builtin == BuiltInTypes.FLOAT_TYPE:
                    return cast(ir.Value, builder.fexp(lhs_value, rhs_value))
                else:
                    return cast(ir.Value, builder.exp(lhs_value, rhs_value))

            assert False
        elif operator in [
            ASTOperator.NOT_EQUAL_OPERATOR,
            ASTOperator.EQUAL_OPERATOR,
        ]:
            if (
                lhs_type.builtin == BuiltInTypes.STRING_TYPE
                and rhs_type.builtin == BuiltInTypes.STRING_TYPE
            ):
                print("WARN: string equality comparison not implemented yet")
            comparison_to_llvm_comparison = {
                ASTOperator.NOT_EQUAL_OPERATOR: "!=",
                ASTOperator.EQUAL_OPERATOR: "==",
            }
            common_builtin = BuiltInTypes.INT_TYPE
            for int_type in num_types:
                if lhs_type.builtin == int_type or rhs_type.builtin == int_type:
                    lhs_value = castType(
                        lhs_value, Type(builtin=int_type), lhs_type, builder
                    )
                    rhs_value = castType(
                        rhs_value, Type(builtin=int_type), rhs_type, builder
                    )
                    common_builtin = int_type

            lhs_exclusive = (
                lhs_type.exclusive.unit_class if lhs_type.exclusive else None
            )
            rhs_exclusive = (
                rhs_type.exclusive.unit_class if rhs_type.exclusive else None
            )

            if not (lhs_exclusive and rhs_exclusive):
                if common_builtin == BuiltInTypes.FLOAT_TYPE:
                    return cast(
                        ir.Value,
                        builder.fcmp_ordered(
                            comparison_to_llvm_comparison[operator],
                            lhs_value,
                            rhs_value,
                        ),
                    )
                else:
                    return cast(
                        ir.Value,
                        builder.icmp_signed(
                            comparison_to_llvm_comparison[operator],
                            lhs_value,
                            rhs_value,
                        ),
                    )
            if lhs_exclusive and rhs_exclusive:
                assert lhs_type.exclusive and rhs_type.exclusive
                for type in modifier_priority_table[lhs_exclusive]:
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
                            common_builtin = BuiltInTypes.FLOAT_TYPE
                            lhs_value = castType(
                                lhs_value,
                                Type(builtin=BuiltInTypes.FLOAT_TYPE),
                                lhs_type,
                                builder,
                            )
                            rhs_value = castType(
                                rhs_value,
                                Type(builtin=BuiltInTypes.FLOAT_TYPE),
                                rhs_type,
                                builder,
                            )

                        lhs_value = convertToUnit(
                            lhs_value, dest_type, lhs_type, builder
                        )
                        rhs_value = convertToUnit(
                            rhs_value, dest_type, rhs_type, builder
                        )
                        break

            if common_builtin == BuiltInTypes.FLOAT_TYPE:
                return cast(
                    ir.Value,
                    builder.fcmp_ordered(
                        comparison_to_llvm_comparison[operator],
                        lhs_value,
                        rhs_value,
                    ),
                )
            else:
                return cast(
                    ir.Value,
                    builder.icmp_signed(
                        comparison_to_llvm_comparison[operator],
                        lhs_value,
                        rhs_value,
                    ),
                )
        elif operator in [
            ASTOperator.LESS_OPERATOR,
            ASTOperator.LESS_OR_EQUAL_OPERATOR,
            ASTOperator.GREATER_OPERATOR,
            ASTOperator.GREATER_OR_EQUAL_OPERATOR,
        ]:
            comparison_to_llvm_comparison = {
                ASTOperator.LESS_OPERATOR: "<",
                ASTOperator.LESS_OR_EQUAL_OPERATOR: "<=",
                ASTOperator.GREATER_OPERATOR: ">",
                ASTOperator.GREATER_OR_EQUAL_OPERATOR: ">=",
            }
            common_builtin = BuiltInTypes.INT_TYPE
            for int_type in num_types:
                if lhs_type.builtin == int_type or rhs_type.builtin == int_type:
                    lhs_value = castType(
                        lhs_value, Type(builtin=int_type), lhs_type, builder
                    )
                    rhs_value = castType(
                        rhs_value, Type(builtin=int_type), rhs_type, builder
                    )
                    common_builtin = int_type

            lhs_exclusive = (
                lhs_type.exclusive.unit_class if lhs_type.exclusive else None
            )
            rhs_exclusive = (
                rhs_type.exclusive.unit_class if rhs_type.exclusive else None
            )

            if not (lhs_exclusive and rhs_exclusive):
                if common_builtin == BuiltInTypes.FLOAT_TYPE:
                    return cast(
                        ir.Value,
                        builder.fcmp_ordered(
                            comparison_to_llvm_comparison[operator],
                            lhs_value,
                            rhs_value,
                        ),
                    )
                else:
                    return cast(
                        ir.Value,
                        builder.icmp_signed(
                            comparison_to_llvm_comparison[operator],
                            lhs_value,
                            rhs_value,
                        ),
                    )

            if lhs_exclusive and rhs_exclusive:
                assert lhs_type.exclusive and rhs_type.exclusive
                for type in modifier_priority_table[lhs_exclusive]:
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
                            common_builtin = BuiltInTypes.FLOAT_TYPE
                            lhs_value = castType(
                                lhs_value,
                                Type(builtin=BuiltInTypes.FLOAT_TYPE),
                                lhs_type,
                                builder,
                            )
                            rhs_value = castType(
                                rhs_value,
                                Type(builtin=BuiltInTypes.FLOAT_TYPE),
                                rhs_type,
                                builder,
                            )

                        lhs_value = convertToUnit(
                            lhs_value, dest_type, lhs_type, builder
                        )
                        rhs_value = convertToUnit(
                            rhs_value, dest_type, rhs_type, builder
                        )
                        break

            if common_builtin == BuiltInTypes.FLOAT_TYPE:
                return cast(
                    ir.Value,
                    builder.fcmp_ordered(
                        comparison_to_llvm_comparison[operator],
                        lhs_value,
                        rhs_value,
                    ),
                )
            else:
                return cast(
                    ir.Value,
                    builder.icmp_signed(
                        comparison_to_llvm_comparison[operator],
                        lhs_value,
                        rhs_value,
                    ),
                )

        elif operator == ASTOperator.AND_OPERATOR:
            lhs_value = castType(
                lhs_value, Type(builtin=BuiltInTypes.BOOL_TYPE), lhs_type, builder
            )
            rhs_value = castType(
                rhs_value, Type(builtin=BuiltInTypes.BOOL_TYPE), rhs_type, builder
            )
            return cast(ir.Value, builder.and_(lhs_value, rhs_value))
        elif operator == ASTOperator.OR_OPERATOR:
            if isinstance(lhs_value, BaseConstant):
                lhs_value = constantToIrConstant(lhs_value, lhs_type)
            if isinstance(rhs_value, BaseConstant):
                rhs_value = constantToIrConstant(rhs_value, rhs_type)
            lhs_value = castType(
                lhs_value, Type(builtin=BuiltInTypes.BOOL_TYPE), lhs_type, builder
            )
            rhs_value = castType(
                rhs_value, Type(builtin=BuiltInTypes.BOOL_TYPE), rhs_type, builder
            )
            return cast(ir.Value, builder.or_(lhs_value, rhs_value))
        elif operator == ASTOperator.ASSIGNMENT_OPERATOR:
            symbol = compileSymbol(lhs, scope)
            assert isinstance(symbol.type, Type)
            assert symbol.ptr
            if isinstance(rhs_value, BaseConstant):
                rhs_value = constantToIrConstant(rhs_value, rhs.data.type)

            if rhs.data.type.exclusive:
                rhs_value = convertToUnit(
                    rhs_value, symbol.type, rhs.data.type, builder
                )
                if unitConversionResultsInFloat(symbol.type, rhs.data.type):
                    rhs.data.type.builtin = BuiltInTypes.FLOAT_TYPE
            rhs_value = castType(rhs_value, symbol.type, rhs.data.type, builder)
            builder.store(rhs_value, symbol.ptr)
            return rhs_value

        elif operator in [
            ASTOperator.PLUS_ASSIGNMENT_OPERATOR,
            ASTOperator.MINUS_ASSIGNMENT_OPERATOR,
            ASTOperator.MULTIPLY_ASSIGNMENT_OPERATOR,
            ASTOperator.DIVIDE_ASSIGNMENT_OPERATOR,
            ASTOperator.MODULO_ASSIGNMENT_OPERATOR,
        ]:
            assert False
        elif operator in [
            ASTOperator.PERCENT_SCALE_OPERATOR,
            ASTOperator.MARKUP_OPERATOR,
            ASTOperator.MARKDOWN_OPERATOR,
        ]:
            if lhs_type.builtin in num_types and rhs_type.builtin in num_types:
                lhs_value = castType(lhs_value, result_type, lhs_type, builder)
                rhs_value = castType(rhs_value, result_type, rhs_type, builder)
            lhs_exclusive = (
                lhs_type.exclusive.unit_class if lhs_type.exclusive else None
            )
            lhs_unit = lhs_type.exclusive.unit if lhs_type.exclusive else None
            rhs_exclusive = (
                rhs_type.exclusive.unit_class if rhs_type.exclusive else None
            )
            rhs_unit = rhs_type.exclusive.unit if rhs_type.exclusive else None
            exclusive_class = (
                result_type.exclusive.unit_class if result_type.exclusive else None
            )
            exclusive_unit = (
                result_type.exclusive.unit if result_type.exclusive else None
            )

            if operator == ASTOperator.PERCENT_SCALE_OPERATOR:
                scale = cast(ir.Value, builder.fmul(rhs_value, PercentScale))
                return cast(ir.Value, builder.fmul(lhs_value, scale))
            elif operator == ASTOperator.MARKUP_OPERATOR:
                scale = cast(ir.Value, builder.fmul(rhs_value, PercentScale))
                markup = cast(ir.Value, builder.fmul(lhs_value, scale))
                return cast(ir.Value, builder.fadd(scale, markup))
            elif operator == ASTOperator.MARKDOWN_OPERATOR:
                scale = cast(ir.Value, builder.fmul(rhs_value, PercentScale))
                markdown = cast(ir.Value, builder.fmul(lhs_value, scale))
                return cast(ir.Value, builder.fsub(scale, markdown))
        assert False

    def compileUnaryOp(
        tree: ASTNode, scope: Scope, builder: ir.IRBuilder
    ) -> Constant | ir.Value:
        operand = tree.data.operand
        operand_expr = compileExpression(operand, scope, builder)
        operator = tree.data.operator
        if operator == ASTOperator.POSITIVE_OPERATOR:
            return operand_expr
        elif operator == ASTOperator.NEGATIVE_OPERATOR:
            if isinstance(operand_expr, BaseConstant):
                if operand_expr.type == BuiltInTypes.INT_TYPE:
                    operand_expr.value *= -1
                elif operand_expr.type == BuiltInTypes.FLOAT_TYPE:
                    operand_expr.value *= -1.0
                return operand_expr
            if operand.data.type.builtin in num_types:
                return cast(ir.Value, builder.sub(Zero, operand_expr))
            elif operand.data.type.builtin == BuiltInTypes.FLOAT_TYPE:
                return cast(ir.Value, builder.fneg(operand_expr))
            assert False
        elif operator == ASTOperator.PRE_INCREMENT_OPERATOR:
            symbol = compileSymbol(operand, scope)
            assert symbol.ptr
            increment = cast(ir.Value, builder.add(builder.load(symbol.ptr), One))
            builder.store(increment, symbol.ptr)
            return increment
        elif operator == ASTOperator.PRE_DECREMENT_OPERATOR:
            symbol = compileSymbol(operand, scope)
            assert symbol.ptr
            decrement = cast(ir.Value, builder.sub(builder.load(symbol.ptr), One))
            builder.store(decrement, symbol.ptr)
            return decrement

        elif operator == ASTOperator.POST_INCREMENT_OPERATOR:
            symbol = compileSymbol(operand, scope)
            assert symbol.ptr
            increment = cast(ir.Value, builder.add(builder.load(symbol.ptr), One))
            builder.store(increment, symbol.ptr)
            return operand_expr
        elif operator == ASTOperator.POST_DECREMENT_OPERATOR:
            symbol = compileSymbol(operand, scope)
            assert symbol.ptr
            decrement = cast(ir.Value, builder.sub(builder.load(symbol.ptr), One))
            builder.store(decrement, symbol.ptr)
            return operand_expr

        elif operator == ASTOperator.NOT_OPERATOR:
            operand_expr = castType(
                operand_expr,
                Type(builtin=BuiltInTypes.BOOL_TYPE),
                operand.data.type,
                builder,
            )
            if isinstance(operand_expr, BaseConstant):
                assert isinstance(operand_expr, BoolConstant)
                operand_expr.value = not operand_expr.value
                return operand_expr
            return cast(ir.Value, builder.not_(operand_expr))
        assert False

    def compileFunctionCall(
        tree: ASTNode, scope: Scope, builder: ir.IRBuilder
    ) -> ir.Value:
        name = compileIdentifier(tree.data.function)
        symbol = reference(scope, name)
        assert isinstance(symbol.type, Function)

        assert symbol.type.func_ir
        func_ir = symbol.type.func_ir

        arguments: list[ir.Value] = []
        for arg in tree.data.arguments:
            arg_expr = compileExpression(arg, scope, builder)
            if isinstance(arg_expr, BaseConstant):
                arg_expr = constantToIrConstant(arg_expr, param.type)
            arguments.append(arg_expr)
        return builder.call(func_ir, arguments)

    def compileLiteral(tree: ASTNode) -> Constant:
        if tree.data.literal_type == ASTLiteral.TRUE_LITERAL:
            tree.data.type = Type(builtin=BuiltInTypes.BOOL_TYPE)
            return BoolConstant(True)
        elif tree.data.literal_type == ASTLiteral.FALSE_LITERAL:
            tree.data.type = Type(builtin=BuiltInTypes.BOOL_TYPE)
            return BoolConstant(False)
        elif tree.data.literal_type == ASTLiteral.INT_LITERAL:
            tree.data.type = Type(builtin=BuiltInTypes.INT_TYPE)
            return IntConstant(int(code[tree.token.start : tree.token.end]))
        elif tree.data.literal_type == ASTLiteral.FLOAT_LITERAL:
            tree.data.type = Type(builtin=BuiltInTypes.FLOAT_TYPE)
            return FloatConstant(float(code[tree.token.start : tree.token.end]))
        elif tree.data.literal_type == ASTLiteral.CHAR_LITERAL:
            tree.data.type = Type(builtin=BuiltInTypes.CHAR_TYPE)
            return CharConstant(code[tree.token.start + 1 : tree.token.end - 1])
        elif tree.data.literal_type == ASTLiteral.STRING_LITERAL:
            tree.data.type = Type(builtin=BuiltInTypes.STRING_TYPE)
            return StringConstant(code[tree.token.start + 1 : tree.token.end - 1])
        assert False

    def reference(scope: Scope, name: str) -> Symbol:
        top_scope = scope
        while top_scope:
            result = top_scope.symbols.get(name)
            if result:
                return result
            top_scope = top_scope.parent_scope
        assert False

    def compileSymbol(tree: ASTNode, scope: Scope) -> Symbol:
        name = compileIdentifier(tree)
        symbol = reference(scope, name)
        return symbol

    def toBool(
        value: ir.Value | Constant, type: Type, builder: ir.IRBuilder
    ) -> ir.Value | Constant:
        if isinstance(value, BaseConstant):
            if value.value:
                return BoolConstant(value=True)
            return BoolConstant(value=False)
        if type.builtin == BuiltInTypes.BOOL_TYPE:
            return value
        elif type.builtin in int_types:
            return builder.icmp_signed("!=", Zero, value)
        elif type.builtin == BuiltInTypes.FLOAT_TYPE:
            return builder.fcmp_ordered("!=", ZeroFloat, value)
        elif type.builtin == BuiltInTypes.STRING_TYPE:
            print("WARN: string to bool not yet implemented")
        assert False

    def toInt(
        value: ir.Value | Constant, type: Type, builder: ir.IRBuilder
    ) -> ir.Value | Constant:
        if type.builtin == BuiltInTypes.INT_TYPE:
            return value
        elif type.builtin in int_types:
            if isinstance(value, BaseConstant):
                if value.type == BuiltInTypes.CHAR_TYPE:
                    return IntConstant(value=ord(value.value))
                return IntConstant(value=int(value.value))
            return cast(ir.Value, builder.sext(value, IntType))
        elif type.builtin == BuiltInTypes.FLOAT_TYPE:
            if isinstance(value, BaseConstant):
                return IntConstant(value=int(value.value))
            return cast(ir.Value, builder.fptosi(value, IntType))
        assert False

    def toFloat(
        value: ir.Value | Constant, type: Type, builder: ir.IRBuilder
    ) -> ir.Value | Constant:
        if type.builtin == BuiltInTypes.FLOAT_TYPE:
            return value
        elif type.builtin in int_types:
            if isinstance(value, BaseConstant):
                if type.builtin == BuiltInTypes.CHAR_TYPE:
                    return FloatConstant(value=float(ord(cast(str, value.value))))
                return FloatConstant(value=float(int(value.value)))
            return builder.sitofp(value, FloatType)  # type: ignore
        assert False

    def toChar(
        value: ir.Value | Constant, type: Type, builder: ir.IRBuilder
    ) -> ir.Value | Constant:
        if type.builtin == BuiltInTypes.CHAR_TYPE:
            return value
        elif type.builtin == BuiltInTypes.INT_TYPE:
            if isinstance(value, BaseConstant):
                return CharConstant(value=chr(cast(int, value.value) % 256))
            return cast(ir.Value, builder.trunc(value, CharType))
        elif type.builtin == BuiltInTypes.BOOL_TYPE:
            if isinstance(value, BaseConstant):
                if value.value:
                    return CharConstant(value=chr(1))
                return CharConstant(value=chr(0))
            return cast(ir.Value, builder.sext(value, CharType))
        elif type.builtin == BuiltInTypes.FLOAT_TYPE:
            if isinstance(value, BaseConstant):
                return CharConstant(value=chr(int(value.value) % 256))
            return cast(ir.Value, builder.fptosi(value, CharType))
        assert False

    def castType(
        value: ir.Value | Constant, dest: Type, src: Type, builder: ir.IRBuilder
    ) -> ir.Value | Constant:
        if dest.builtin == BuiltInTypes.INT_TYPE:
            return toInt(value, src, builder)
        elif dest.builtin == BuiltInTypes.FLOAT_TYPE:
            return toFloat(value, src, builder)
        elif dest.builtin == BuiltInTypes.BOOL_TYPE:
            return toBool(value, src, builder)
        elif dest.builtin == BuiltInTypes.CHAR_TYPE:
            return toChar(value, src, builder)
        elif dest.builtin == BuiltInTypes.STRING_TYPE:
            return value
        assert False

    def convertToUnit(
        value: ir.Value | Constant,
        dest_type: Type,
        src_type: Type,
        builder: ir.IRBuilder,
    ) -> ir.Value | Constant:
        assert dest_type.exclusive and src_type.exclusive
        dest_unit = dest_type.exclusive.unit
        src_unit = src_type.exclusive.unit

        if dest_unit == src_unit:
            return value
        elif src_unit in multiple_based_units:
            has_baked = baked_multiple_conversion_table.get((src_unit, dest_unit))
            assert has_baked
            is_float, factor = has_baked
            if is_float or src_type.builtin == BuiltInTypes.FLOAT_TYPE:
                if src_type.builtin == BuiltInTypes.INT_TYPE:
                    value = castType(
                        value, Type(builtin=BuiltInTypes.FLOAT_TYPE), src_type, builder
                    )
                if isinstance(value, BaseConstant):
                    if value.type == BuiltInTypes.FLOAT_TYPE:
                        return FloatConstant(value=value.value * factor)
                return cast(
                    ir.Value, builder.fmul(value, ir.Constant(FloatType, factor))
                )
            else:
                if isinstance(value, BaseConstant):
                    if value.type == BuiltInTypes.INT_TYPE:
                        return IntConstant(value=value.value * round(factor))
                return cast(
                    ir.Value, builder.mul(value, ir.Constant(IntType, round(factor)))
                )

        elif (
            dest_unit == ModifierTypes.KELV_TYPE and src_unit == ModifierTypes.CELC_TYPE
        ):
            if src_type.builtin == BuiltInTypes.INT_TYPE:
                value = castType(
                    value, Type(builtin=BuiltInTypes.FLOAT_TYPE), src_type, builder
                )
            if (
                isinstance(value, BaseConstant)
                and value.type == BuiltInTypes.FLOAT_TYPE
            ):
                return FloatConstant(value=value.value + 273.15)
            return cast(ir.Value, builder.fadd(value, ir.Constant(FloatType, 273.15)))
        elif (
            dest_unit == ModifierTypes.KELV_TYPE and src_unit == ModifierTypes.FAHR_TYPE
        ):
            if src_type.builtin == BuiltInTypes.INT_TYPE:
                value = castType(
                    value, Type(builtin=BuiltInTypes.FLOAT_TYPE), src_type, builder
                )
            if (
                isinstance(value, BaseConstant)
                and value.type == BuiltInTypes.FLOAT_TYPE
            ):
                return FloatConstant(value=(value.value + 459.67) * (5.0 / 9.0))
            return cast(
                ir.Value,
                builder.fmul(
                    builder.fadd(value, ir.Constant(FloatType, 459.67)),
                    ir.Constant(FloatType, 5.0 / 9.0),
                ),
            )
        elif (
            dest_unit == ModifierTypes.CELC_TYPE and src_unit == ModifierTypes.KELV_TYPE
        ):
            if src_type.builtin == BuiltInTypes.INT_TYPE:
                value = castType(
                    value, Type(builtin=BuiltInTypes.FLOAT_TYPE), src_type, builder
                )
            if (
                isinstance(value, BaseConstant)
                and value.type == BuiltInTypes.FLOAT_TYPE
            ):
                return FloatConstant(value=value.value - 273.15)
            return cast(ir.Value, builder.fsub(value, ir.Constant(FloatType, 273.15)))
        elif (
            dest_unit == ModifierTypes.CELC_TYPE and src_unit == ModifierTypes.FAHR_TYPE
        ):
            if src_type.builtin == BuiltInTypes.INT_TYPE:
                value = castType(
                    value, Type(builtin=BuiltInTypes.FLOAT_TYPE), src_type, builder
                )
            if (
                isinstance(value, BaseConstant)
                and value.type == BuiltInTypes.FLOAT_TYPE
            ):
                return FloatConstant(value=(value.value - 32.0) * (5.0 / 9.0))
            return cast(
                ir.Value,
                builder.fmul(
                    builder.fsub(value, ir.Constant(FloatType, 32.0)),
                    ir.Constant(FloatType, 5.0 / 9.0),
                ),
            )
        elif (
            dest_unit == ModifierTypes.FAHR_TYPE and src_unit == ModifierTypes.KELV_TYPE
        ):
            if src_type.builtin == BuiltInTypes.INT_TYPE:
                value = castType(
                    value, Type(builtin=BuiltInTypes.FLOAT_TYPE), src_type, builder
                )
            if (
                isinstance(value, BaseConstant)
                and value.type == BuiltInTypes.FLOAT_TYPE
            ):
                return FloatConstant(value=(value.value * (9.0 / 5.0)) - 459.67)
            return cast(
                ir.Value,
                builder.fsub(
                    builder.mul(value, ir.Constant(FloatType, 9.0 / 5.0)),
                    ir.Constant(FloatType, 459.67),
                ),
            )
        elif (
            dest_unit == ModifierTypes.FAHR_TYPE and src_unit == ModifierTypes.CELC_TYPE
        ):
            if src_type.builtin == BuiltInTypes.INT_TYPE:
                value = castType(
                    value, Type(builtin=BuiltInTypes.FLOAT_TYPE), src_type, builder
                )
            if (
                isinstance(value, BaseConstant)
                and value.type == BuiltInTypes.FLOAT_TYPE
            ):
                return FloatConstant(value=(value.value * (9.0 / 5.0)) + 32.0)
            return cast(
                ir.Value,
                builder.fadd(
                    builder.fmul(value, ir.Constant(FloatType, 9.0 / 5.0)),
                    ir.Constant(FloatType, 32.0),
                ),
            )

        assert False

    def typeToIrType(type: Type) -> ir.Type:
        if type.builtin == BuiltInTypes.VOID_TYPE:
            return VoidType
        elif type.builtin == BuiltInTypes.INT_TYPE:
            return IntType
        elif type.builtin == BuiltInTypes.FLOAT_TYPE:
            return FloatType
        elif type.builtin == BuiltInTypes.BOOL_TYPE:
            return BoolType
        elif type.builtin == BuiltInTypes.CHAR_TYPE:
            return CharType
        elif type.builtin == BuiltInTypes.STRING_TYPE:
            return StringType
        assert False

    def constantToIrConstant(constant: Constant, type: Type) -> ir.Constant:
        nonlocal str_counter
        if type.builtin == BuiltInTypes.INT_TYPE:
            return ir.Constant(IntType, constant.value)
        elif type.builtin == BuiltInTypes.FLOAT_TYPE:
            return ir.Constant(FloatType, constant.value)
        elif type.builtin == BuiltInTypes.BOOL_TYPE:
            return ir.Constant(BoolType, constant.value)
        elif type.builtin == BuiltInTypes.CHAR_TYPE:
            assert isinstance(constant.value, str)
            return ir.Constant(CharType, ord(constant.value))
        elif type.builtin == BuiltInTypes.STRING_TYPE:
            assert isinstance(constant.value, str)
            string_u8 = bytearray(constant.value.encode("utf8")) + b"\0"
            str_type = ir.ArrayType(CharType, len(string_u8))

            global_str = ir.GlobalVariable(module, str_type, name=f".str{str_counter}")
            str_counter += 1
            global_str.linkage = "private"
            global_str.global_constant = True
            global_str.initializer = ir.Constant(str_type, string_u8)  # type: ignore
            ptr = global_str.gep((Zero, Zero))
            return ptr
        assert False

    builder = ir.IRBuilder()
    alloca_block = None

    for node in tree.data.children:
        if node.kind == ASTNodeType.FUNCTION_STMT:
            compileFunctionStmt(node, scope, builder)
        elif node.kind == ASTNodeType.DECLARATION:
            compileDeclaration(node, scope, builder, alloca_block)

    file = open(dest_file, "w")
    file.write(str(module))
    file.close()
    return module
