from __future__ import annotations
from dataclasses import dataclass
from typing import Counter
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
    Function,
    Scope,
    BuiltInTypes,
    ModifierClass,
    Symbol,
    Type,
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
                return builder.sub(Zero, operand_expr)  # type: ignore
            elif operand.data.type.builtin == BuiltInTypes.FLOAT_TYPE:
                return builder.fneg(operand_expr)  # type: ignore
            assert False
        elif operator == ASTOperator.PRE_INCREMENT_OPERATOR:
            symbol = compileSymbol(operand, scope)
            assert symbol.ptr
            increment: ir.Value = builder.add(builder.load(symbol.ptr), One)  # type: ignore
            builder.store(increment, symbol.ptr)
            return increment
        elif operator == ASTOperator.PRE_DECREMENT_OPERATOR:
            symbol = compileSymbol(operand, scope)
            assert symbol.ptr
            decrement: ir.Value = builder.sub(builder.load(symbol.ptr), One)  # type: ignore
            builder.store(decrement, symbol.ptr)
            return decrement

        elif operator == ASTOperator.POST_INCREMENT_OPERATOR:
            symbol = compileSymbol(operand, scope)
            assert symbol.ptr
            increment: ir.Value = builder.add(builder.load(symbol.ptr), One)  # type: ignore
            builder.store(increment, symbol.ptr)
            return operand_expr
        elif operator == ASTOperator.POST_DECREMENT_OPERATOR:
            symbol = compileSymbol(operand, scope)
            assert symbol.ptr
            decrement: ir.Value = builder.sub(builder.load(symbol.ptr), One)  # type: ignore
            builder.store(decrement, symbol.ptr)
            return operand_expr

        elif operator == ASTOperator.NOT_OPERATOR:
            if isinstance(operand_expr, BaseConstant):
                assert isinstance(operand_expr, BoolConstant)
                operand_expr.value = not operand_expr.value
                return operand_expr
            return builder.not_(operand_expr)  # type: ignore
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

    def toBool(value: ir.Value, type: Type, builder: ir.IRBuilder):
        if type.builtin == BuiltInTypes.BOOL_TYPE:
            return value
        elif type.builtin in int_types:
            return builder.icmp_unsigned("!=", Zero, value)
        elif type.builtin == BuiltInTypes.FLOAT_TYPE:
            return builder.fcmp_unordered("!=", ZeroFloat, value)
        elif type.builtin == BuiltInTypes.STRING_TYPE:
            print("WARN: string to bool not yet implemented")
        assert False

    def toInt(value: ir.Value, type: Type, builder: ir.IRBuilder):
        if type.builtin == BuiltInTypes.INT_TYPE:
            return value
        elif type.builtin in int_types:
            return builder.sext(value, IntType)
        elif type.builtin == BuiltInTypes.FLOAT_TYPE:
            return builder.fptosi(value, IntType)
        assert False

    def toFloat(value: ir.Value, type: Type, builder: ir.IRBuilder):
        if type.builtin == BuiltInTypes.FLOAT_TYPE:
            return value
        elif type.builtin in int_types:
            return builder.sitofp(value, FloatType)
        assert False

    def toChar(value: ir.Value, type: Type, builder: ir.IRBuilder):
        if type.builtin == BuiltInTypes.CHAR_TYPE:
            return value
        elif type.builtin == BuiltInTypes.INT_TYPE:
            return builder.trunc(value, CharType)
        elif type.builtin == BuiltInTypes.BOOL_TYPE:
            return builder.sext(value, CharType)
        elif type.builtin == BuiltInTypes.FLOAT_TYPE:
            return builder.fptosi(value, CharType)
        assert False

    def castType(value: ir.Value, dest: Type, src: Type, builder: ir.IRBuilder):
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
