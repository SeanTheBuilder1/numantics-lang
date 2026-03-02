from lexer_token import Token, TokenType
from syntax_types import Node, NodeType
from result import Ok, Error, Result


def parseFile(tokens: list[Token]) -> tuple[Node, bool]:
    token_index = 0
    tokens_len = len(tokens)
    current_token: Token = tokens[token_index]
    has_error = False

    def checkToken(offset=0) -> Token:
        nonlocal token_index, current_token
        check_index = token_index + offset
        if check_index >= tokens_len:
            return tokens[-1]
        return tokens[check_index]

    def nextToken() -> Token:
        nonlocal token_index, current_token
        token_index = token_index + 1
        if token_index >= tokens_len:
            current_token = tokens[-1]
        else:
            current_token = tokens[token_index]
        return current_token

    def errorFactory(err_str: str) -> Node:
        nonlocal has_error
        has_error = True
        return Node(kind=NodeType.ERROR, children=[], token=checkToken(), data=err_str)

    def expect(type: TokenType, err_str: str) -> Node | None:
        if checkToken().type != type:
            error = errorFactory(err_str)
            nextToken()
            return error
        nextToken()
        return None

    def expectNonConsuming(type: TokenType, err_str: str) -> Node | None:
        if checkToken().type != type:
            error = errorFactory(err_str)
            return error
        return None

    def expectNode(
        type: TokenType, err_str: str, node_type: NodeType
    ) -> Result[Node, Node]:
        if checkToken().type != type:
            error = Error(errorFactory(err_str))
            nextToken()
            return error
        node = Node(kind=node_type, children=[], token=checkToken(), data=None)
        nextToken()
        return Ok(node)

    def expectNodeNonConsuming(
        type: TokenType, err_str: str, node_type: NodeType
    ) -> Result[Node, Node]:
        if checkToken().type != type:
            error = Error(errorFactory(err_str))
            return error
        node = Node(kind=node_type, children=[], token=checkToken(), data=None)
        return Ok(node)

    def recoverError(token_list: list[TokenType]):
        recoverErrorNonConsuming(token_list)
        if current_token.type in token_list:
            nextToken()

    def recoverErrorNonConsuming(token_list: list[TokenType]):
        while (
            current_token.type not in token_list
            and current_token.type != TokenType.ENDMARKER
        ):
            nextToken()

    def parseCompoundType() -> Result[Node, Node]:
        node = Node(NodeType.COMPOUND_TYPE, children=[], token=checkToken(), data=None)
        if checkToken().type in [
            TokenType.VOID_TYPE,
            TokenType.INT_TYPE,
            TokenType.FLOAT_TYPE,
            TokenType.BOOL_TYPE,
            TokenType.CHAR_TYPE,
            TokenType.STRING_TYPE,
        ]:
            node.children.append(
                Node(NodeType.BUILTIN_TYPE, children=[], token=checkToken(), data=None)
            )
            nextToken()
        else:
            return Error(errorFactory("Type expected"))

        error = expect(TokenType.OPEN_ANGLE_DELIMITER, "'<' expected in compound type")
        if error:
            return Error(error)
        if checkToken().type in [
            TokenType.PERCENT_TYPE,
            TokenType.XPERCENT_TYPE,
            TokenType.POSITIVE_TYPE,
            TokenType.NEGATIVE_TYPE,
            TokenType.NONZERO_TYPE,
            TokenType.EVEN_TYPE,
            TokenType.ODD_TYPE,
            TokenType.AUTO_TYPE,
            TokenType.SECOND_TYPE,
            TokenType.MINUTE_TYPE,
            TokenType.HOUR_TYPE,
            TokenType.DAY_TYPE,
            TokenType.WEEK_TYPE,
            TokenType.MONTH_TYPE,
            TokenType.YEAR_TYPE,
            TokenType.METER_TYPE,
            TokenType.MM_TYPE,
            TokenType.CM_TYPE,
            TokenType.KM_TYPE,
            TokenType.FT_TYPE,
            TokenType.INCH_TYPE,
            TokenType.METER2_TYPE,
            TokenType.MM2_TYPE,
            TokenType.CM2_TYPE,
            TokenType.KM2_TYPE,
            TokenType.FT2_TYPE,
            TokenType.INCH2_TYPE,
            TokenType.LITER_TYPE,
            TokenType.ML_TYPE,
            TokenType.CL_TYPE,
            TokenType.KL_TYPE,
            TokenType.GRAM_TYPE,
            TokenType.MG_TYPE,
            TokenType.CG_TYPE,
            TokenType.KG_TYPE,
            TokenType.CELC_TYPE,
            TokenType.FAHR_TYPE,
            TokenType.KELV_TYPE,
            TokenType.NEWT_TYPE,
            TokenType.KGF_TYPE,
            TokenType.LBF_TYPE,
            TokenType.MPS_TYPE,
            TokenType.FPS_TYPE,
            TokenType.MPS2_TYPE,
        ]:
            node.children.append(
                Node(
                    kind=NodeType.MODIFIER_TYPE,
                    children=[],
                    token=checkToken(),
                    data=None,
                )
            )
            nextToken()
        else:
            return Error(errorFactory("expected modifier type"))

        while checkToken().type == TokenType.COMMA_DELIMITER:
            error = expect(TokenType.COMMA_DELIMITER, "',' expected in compound type")
            if error:
                return Error(error)

            if checkToken().type in [
                TokenType.PERCENT_TYPE,
                TokenType.XPERCENT_TYPE,
                TokenType.POSITIVE_TYPE,
                TokenType.NEGATIVE_TYPE,
                TokenType.NONZERO_TYPE,
                TokenType.EVEN_TYPE,
                TokenType.ODD_TYPE,
                TokenType.AUTO_TYPE,
                TokenType.SECOND_TYPE,
                TokenType.MINUTE_TYPE,
                TokenType.HOUR_TYPE,
                TokenType.DAY_TYPE,
                TokenType.WEEK_TYPE,
                TokenType.MONTH_TYPE,
                TokenType.YEAR_TYPE,
                TokenType.METER_TYPE,
                TokenType.MM_TYPE,
                TokenType.CM_TYPE,
                TokenType.KM_TYPE,
                TokenType.FT_TYPE,
                TokenType.INCH_TYPE,
                TokenType.METER2_TYPE,
                TokenType.MM2_TYPE,
                TokenType.CM2_TYPE,
                TokenType.KM2_TYPE,
                TokenType.FT2_TYPE,
                TokenType.INCH2_TYPE,
                TokenType.LITER_TYPE,
                TokenType.ML_TYPE,
                TokenType.CL_TYPE,
                TokenType.KL_TYPE,
                TokenType.GRAM_TYPE,
                TokenType.MG_TYPE,
                TokenType.CG_TYPE,
                TokenType.KG_TYPE,
                TokenType.CELC_TYPE,
                TokenType.FAHR_TYPE,
                TokenType.KELV_TYPE,
                TokenType.NEWT_TYPE,
                TokenType.KGF_TYPE,
                TokenType.LBF_TYPE,
                TokenType.MPS_TYPE,
                TokenType.FPS_TYPE,
                TokenType.MPS2_TYPE,
            ]:
                node.children.append(
                    Node(
                        kind=NodeType.MODIFIER_TYPE,
                        children=[],
                        token=checkToken(),
                        data=None,
                    )
                )
                nextToken()
            else:
                return Error(errorFactory("expected modifier type"))

        error = expect(
            TokenType.CLOSED_ANGLE_DELIMITER, "'>' expected in compound type"
        )
        if error:
            return Error(error)
        return Ok(node)

    def parseType() -> Result[Node, Node]:
        if checkToken(1).type == TokenType.OPEN_ANGLE_DELIMITER:
            return parseCompoundType()

        if checkToken().type in [
            TokenType.VOID_TYPE,
            TokenType.INT_TYPE,
            TokenType.FLOAT_TYPE,
            TokenType.BOOL_TYPE,
            TokenType.CHAR_TYPE,
            TokenType.STRING_TYPE,
        ]:
            node = Node(
                kind=NodeType.BUILTIN_TYPE,
                children=[],
                token=checkToken(),
                data=None,
            )
            nextToken()
            return Ok(node)
        return Error(errorFactory("Type expected"))

    def parseParameterList() -> Result[Node, Node]:
        node = Node(NodeType.PARAMETER_LIST, children=[], token=checkToken(), data=None)
        result = parseType()
        if isinstance(result, Error):
            return result
        node.children.append(result.ok_value())
        result = expectNode(
            TokenType.IDENTIFIER, "expected parameter name", NodeType.IDENTIFIER
        )
        if isinstance(result, Error):
            return result
        node.children.append(result.ok_value())

        while checkToken().type == TokenType.COMMA_DELIMITER:
            error = expect(TokenType.COMMA_DELIMITER, "',' expected in parameter list")
            if error:
                return Error(error)
            result = parseType()
            if isinstance(result, Error):
                return result
            node.children.append(result.ok_value())
            result = expectNode(
                TokenType.IDENTIFIER,
                "expected parameter name in parameter list",
                NodeType.IDENTIFIER,
            )
            if isinstance(result, Error):
                return result
            node.children.append(result.ok_value())

        return Ok(node)

    def parseIfStmt() -> Result[Node, Node]:
        node = Node(kind=NodeType.IF_STMT, children=[], token=checkToken(), data=None)

        error = expect(TokenType.IF_STATEMENT, "if expected")
        if error:
            return Error(error)

        error = expect(
            TokenType.OPEN_PARENTHESIS_DELIMITER, "'(' expected in if statement"
        )
        if error:
            return Error(error)

        result = parseExpression()
        if isinstance(result, Error):
            return result
        node.children.append(result.ok_value())

        error = expect(
            TokenType.CLOSED_PARENTHESIS_DELIMITER, "')' expected in if statement"
        )
        if error:
            return Error(error)

        result = parseBlock()
        if isinstance(result, Error):
            return result
        node.children.append(result.ok_value())

        if checkToken().type == TokenType.ELIF_STATEMENT:
            result = parseElIfStmt()
            if isinstance(result, Error):
                return result
            node.children.append(result.ok_value())
        elif checkToken().type == TokenType.ELSE_STATEMENT:
            result = parseElseStmt()
            if isinstance(result, Error):
                return result
            node.children.append(result.ok_value())

        return Ok(node)

    def parseElIfStmt() -> Result[Node, Node]:
        node = Node(kind=NodeType.ELIF_STMT, children=[], token=checkToken(), data=None)

        error = expect(TokenType.ELIF_STATEMENT, "elif expected")
        if error:
            return Error(error)

        error = expect(
            TokenType.OPEN_PARENTHESIS_DELIMITER, "'(' expected in elif statement"
        )
        if error:
            return Error(error)

        result = parseExpression()
        if isinstance(result, Error):
            return result
        node.children.append(result.ok_value())

        error = expect(
            TokenType.CLOSED_PARENTHESIS_DELIMITER, "')' expected in elif statement"
        )
        if error:
            return Error(error)

        result = parseBlock()
        if isinstance(result, Error):
            return result
        node.children.append(result.ok_value())

        if checkToken().type == TokenType.ELIF_STATEMENT:
            result = parseElIfStmt()
            if isinstance(result, Error):
                return result
            node.children.append(result.ok_value())
        elif checkToken().type == TokenType.ELSE_STATEMENT:
            result = parseElseStmt()
            if isinstance(result, Error):
                return result
            node.children.append(result.ok_value())

        return Ok(node)

    def parseElseStmt() -> Result[Node, Node]:
        node = Node(kind=NodeType.ELSE_STMT, children=[], token=checkToken(), data=None)

        error = expect(TokenType.ELSE_STATEMENT, "else expected")
        if error:
            return Error(error)

        result = parseBlock()
        if isinstance(result, Error):
            return result
        node.children.append(result.ok_value())

        return Ok(node)

    def parseSwitchStmt() -> Result[Node, Node]:
        node = Node(
            kind=NodeType.SWITCH_STMT, children=[], token=checkToken(), data=None
        )

        error = expect(TokenType.SWITCH_STATEMENT, "switch expected")
        if error:
            return Error(error)

        error = expect(TokenType.OPEN_PARENTHESIS_DELIMITER, "'(' expected in switch")
        if error:
            return Error(error)

        result = parseExpression()
        if isinstance(result, Error):
            return result
        node.children.append(result.ok_value())

        error = expect(TokenType.CLOSED_PARENTHESIS_DELIMITER, "')' expected in switch")
        if error:
            return Error(error)

        result = parseSwitchBody()
        if isinstance(result, Error):
            return result
        node.children.append(result.ok_value())

        return Ok(node)

    def parseSwitchBody() -> Result[Node, Node]:
        node = Node(
            kind=NodeType.SWITCH_BODY, children=[], token=checkToken(), data=None
        )

        error = expect(TokenType.OPEN_CURLY_DELIMITER, "'{' expected in switch body")
        if error:
            return Error(error)

        if checkToken().type == TokenType.DEFAULT_STATEMENT:
            result = parseSwitchDefault()
            if isinstance(result, Error):
                return result
            node.children.append(result.ok_value())
        else:
            result = parseSwitchCase()
            if isinstance(result, Error):
                return result
            node.children.append(result.ok_value())
            while checkToken().type == TokenType.CASE_STATEMENT:
                result = parseSwitchCase()
                if isinstance(result, Error):
                    return result
                node.children.append(result.ok_value())
            if checkToken().type == TokenType.DEFAULT_STATEMENT:
                result = parseSwitchDefault()
                if isinstance(result, Error):
                    return result
                node.children.append(result.ok_value())

        error = expect(TokenType.CLOSED_CURLY_DELIMITER, "'}' expected in switch body")
        if error:
            return Error(error)

        return Ok(node)

    def parseSwitchCase() -> Result[Node, Node]:
        node = Node(
            kind=NodeType.SWITCH_CASE, children=[], token=checkToken(), data=None
        )

        error = expect(TokenType.CASE_STATEMENT, "case expected in switch")
        if error:
            return Error(error)

        result = parseExpression()
        if isinstance(result, Error):
            return result
        node.children.append(result.ok_value())

        error = expect(TokenType.COLON_DELIMITER, "':' expected in switch case")
        if error:
            return Error(error)

        result = parseStatement()
        if isinstance(result, Error):
            return result
        node.children.append(result.ok_value())

        return Ok(node)

    def parseSwitchDefault() -> Result[Node, Node]:
        node = Node(
            kind=NodeType.SWITCH_DEFAULT, children=[], token=checkToken(), data=None
        )

        error = expect(TokenType.DEFAULT_STATEMENT, "default expected in switch")
        if error:
            return Error(error)

        error = expect(TokenType.COLON_DELIMITER, "':' expected in switch default")
        if error:
            return Error(error)

        result = parseStatement()
        if isinstance(result, Error):
            return result
        node.children.append(result.ok_value())

        return Ok(node)

    def parseSweepStmt() -> Result[Node, Node]:
        node = Node(
            kind=NodeType.SWEEP_STMT, children=[], token=checkToken(), data=None
        )

        error = expect(TokenType.SWEEP_STATEMENT, "sweep expected")
        if error:
            return Error(error)

        error = expect(TokenType.OPEN_PARENTHESIS_DELIMITER, "'(' expected in sweep")
        if error:
            return Error(error)

        result = parseExpression()
        if isinstance(result, Error):
            return result
        node.children.append(result.ok_value())

        error = expect(TokenType.CLOSED_PARENTHESIS_DELIMITER, "')' expected in sweep")
        if error:
            return Error(error)

        result = parseSweepBody()
        if isinstance(result, Error):
            return result
        node.children.append(result.ok_value())

        return Ok(node)

    def parseSweepBody() -> Result[Node, Node]:
        node = Node(
            kind=NodeType.SWEEP_BODY, children=[], token=checkToken(), data=None
        )

        error = expect(TokenType.OPEN_CURLY_DELIMITER, "'{' expected in sweep body")
        if error:
            return Error(error)

        if checkToken().type == TokenType.DEFAULT_STATEMENT:
            result = parseSweepDefault()
            if isinstance(result, Error):
                return result
            node.children.append(result.ok_value())
        else:
            result = parseSweepCase()
            if isinstance(result, Error):
                return result
            node.children.append(result.ok_value())
            while checkToken().type == TokenType.RANGE_STATEMENT:
                result = parseSweepCase()
                if isinstance(result, Error):
                    return result
                node.children.append(result.ok_value())
            if checkToken().type == TokenType.DEFAULT_STATEMENT:
                result = parseSweepDefault()
                if isinstance(result, Error):
                    return result
                node.children.append(result.ok_value())

        error = expect(TokenType.CLOSED_CURLY_DELIMITER, "'}' expected in sweep body")
        if error:
            return Error(error)

        return Ok(node)

    def parseSweepCase() -> Result[Node, Node]:
        node = Node(
            kind=NodeType.SWEEP_RANGE, children=[], token=checkToken(), data=None
        )

        error = expect(TokenType.RANGE_STATEMENT, "range expected in sweep")
        if error:
            return Error(error)

        result = parseExpression()
        if isinstance(result, Error):
            return result
        node.children.append(result.ok_value())

        error = expect(TokenType.COLON_DELIMITER, "':' expected in sweep case")
        if error:
            return Error(error)

        result = parseStatement()
        if isinstance(result, Error):
            return result
        node.children.append(result.ok_value())

        return Ok(node)

    def parseSweepDefault() -> Result[Node, Node]:
        node = Node(
            kind=NodeType.SWEEP_DEFAULT, children=[], token=checkToken(), data=None
        )

        error = expect(TokenType.DEFAULT_STATEMENT, "default expected in sweep")
        if error:
            return Error(error)

        error = expect(TokenType.COLON_DELIMITER, "':' expected in sweep default")
        if error:
            return Error(error)

        result = parseStatement()
        if isinstance(result, Error):
            return result
        node.children.append(result.ok_value())

        return Ok(node)

    def parseWhileStmt() -> Result[Node, Node]:
        node = Node(
            kind=NodeType.WHILE_STMT, children=[], token=checkToken(), data=None
        )
        error = expect(TokenType.WHILE_LOOP, "while expected")
        if error:
            return Error(error)

        error = expect(
            TokenType.OPEN_PARENTHESIS_DELIMITER, "'(' expected in while statement"
        )
        if error:
            return Error(error)

        result = parseExpression()
        if isinstance(result, Error):
            return result
        node.children.append(result.ok_value())

        if checkToken().type == TokenType.COMMA_DELIMITER:
            error = expect(TokenType.COMMA_DELIMITER, "',' expected in while statement")
            if error:
                return Error(error)

            result = parseExpression()
            if isinstance(result, Error):
                return result
            node.children.append(result.ok_value())

        error = expect(
            TokenType.CLOSED_PARENTHESIS_DELIMITER, "')' expected in while statement"
        )
        if error:
            return Error(error)

        result = parseBlock()
        if isinstance(result, Error):
            return result
        node.children.append(result.ok_value())

        return Ok(node)

    def parseForStmt() -> Result[Node, Node]:
        node = Node(kind=NodeType.FOR_STMT, children=[], token=checkToken(), data=None)
        error = expect(TokenType.FOR_LOOP, "for expected")
        if error:
            return Error(error)

        error = expect(
            TokenType.OPEN_PARENTHESIS_DELIMITER, "'(' expected in for statement"
        )
        if error:
            return Error(error)

        if checkToken().type == TokenType.SEMI_COLON_DELIMITER:
            node.children.append(
                Node(kind=NodeType.EMPTY, children=[], token=checkToken(), data=None)
            )
            error = expect(
                TokenType.SEMI_COLON_DELIMITER, "';' expected in for statement"
            )
            if error:
                return Error(error)
        elif checkToken().type in [
            TokenType.VOID_TYPE,
            TokenType.INT_TYPE,
            TokenType.FLOAT_TYPE,
            TokenType.BOOL_TYPE,
            TokenType.CHAR_TYPE,
            TokenType.STRING_TYPE,
        ]:
            result = parseDeclaration()
            if isinstance(result, Error):
                return result
            node.children.append(result.ok_value())
            error = expect(
                TokenType.SEMI_COLON_DELIMITER, "';' expected in for statement"
            )
            if error:
                return Error(error)
        else:
            result = parseExpression()
            if isinstance(result, Error):
                return result
            node.children.append(result.ok_value())
            error = expect(
                TokenType.SEMI_COLON_DELIMITER, "';' expected in for statement"
            )
            if error:
                return Error(error)

        if checkToken().type == TokenType.SEMI_COLON_DELIMITER:
            node.children.append(
                Node(kind=NodeType.EMPTY, children=[], token=checkToken(), data=None)
            )
            error = expect(
                TokenType.SEMI_COLON_DELIMITER, "';' expected in for statement"
            )
            if error:
                return Error(error)
        else:
            result = parseExpression()
            if isinstance(result, Error):
                return result
            node.children.append(result.ok_value())
            error = expect(
                TokenType.SEMI_COLON_DELIMITER, "';' expected in for statement"
            )
            if error:
                return Error(error)

        if checkToken().type == TokenType.CLOSED_PARENTHESIS_DELIMITER:
            node.children.append(
                Node(kind=NodeType.EMPTY, children=[], token=checkToken(), data=None)
            )
            error = expect(
                TokenType.CLOSED_PARENTHESIS_DELIMITER, "')' expected in for statement"
            )
            if error:
                return Error(error)
        else:
            result = parseExpression()
            if isinstance(result, Error):
                return result
            node.children.append(result.ok_value())
            error = expect(
                TokenType.CLOSED_PARENTHESIS_DELIMITER, "')' expected in for statement"
            )
            if error:
                return Error(error)

        result = parseBlock()
        if isinstance(result, Error):
            return result
        node.children.append(result.ok_value())

        return Ok(node)

    def parseDeclaration() -> Result[Node, Node]:
        node = Node(
            kind=NodeType.DECLARATION, children=[], token=checkToken(), data=None
        )
        result = parseType()
        if isinstance(result, Error):
            return result
        node.children.append(result.ok_value())

        result = expectNode(
            TokenType.IDENTIFIER, "variable name expected", NodeType.IDENTIFIER
        )
        if isinstance(result, Error):
            return result
        node.children.append(result.ok_value())

        if checkToken().type == TokenType.ASSIGNMENT_OP:
            error = expect(TokenType.ASSIGNMENT_OP, "'=' expected in declaration")
            if error:
                return Error(error)
            result = parseExpression()
            if isinstance(result, Error):
                return result
            node.children.append(result.ok_value())

        return Ok(node)

    def parseDeclarationStmt() -> Result[Node, Node]:
        node = Node(
            kind=NodeType.DECLARATION_STMT, children=[], token=checkToken(), data=None
        )
        result = parseDeclaration()
        if isinstance(result, Error):
            return result
        node.children.append(result.ok_value())

        error = expect(
            TokenType.SEMI_COLON_DELIMITER, "';' expected in declaration statement"
        )
        if error:
            return Error(error)

        return Ok(node)

    def parseNextStmt() -> Result[Node, Node]:
        node = Node(kind=NodeType.NEXT_STMT, children=[], token=checkToken(), data=None)
        error = expect(TokenType.NEXT_STATEMENT, "next expected")
        if error:
            return Error(error)
        error = expect(TokenType.SEMI_COLON_DELIMITER, "';' expected in next statement")
        if error:
            return Error(error)
        return Ok(node)

    def parseStopStmt() -> Result[Node, Node]:
        node = Node(kind=NodeType.STOP_STMT, children=[], token=checkToken(), data=None)
        error = expect(TokenType.STOP_STATEMENT, "stop expected")
        if error:
            return Error(error)
        error = expect(TokenType.SEMI_COLON_DELIMITER, "';' expected in stop statement")
        if error:
            return Error(error)
        return Ok(node)

    def parseReturnStmt() -> Result[Node, Node]:
        node = Node(
            kind=NodeType.RETURN_STMT, children=[], token=checkToken(), data=None
        )
        error = expect(TokenType.RETURN_STATEMENT, "return expected")
        if error:
            return Error(error)
        if current_token.type != TokenType.SEMI_COLON_DELIMITER:
            result = parseExpression()
            if isinstance(result, Error):
                return result
            node.children.append(result.ok_value())
        error = expect(
            TokenType.SEMI_COLON_DELIMITER, "';' expected in return statement"
        )
        if error:
            return Error(error)
        return Ok(node)

    def parseExpressionStmt():
        node = Node(
            kind=NodeType.EXPRESSION_STMT,
            children=[],
            token=checkToken(),
            data=None,
        )

        result = parseExpression()
        if isinstance(result, Error):
            return result
        node.children.append(result.ok_value())

        error = expect(
            TokenType.SEMI_COLON_DELIMITER, "';' expected in expression statement"
        )
        if error:
            return Error(error)

        return Ok(node)

    def parseExpression() -> Result[Node, Node]:
        node = Node(
            kind=NodeType.EXPRESSION, children=[], token=checkToken(), data=None
        )
        result = parseNumanticsOperation()
        if isinstance(result, Error):
            return result
        node.children.append(result.ok_value())
        return Ok(node)

    def parseNumanticsOperation() -> Result[Node, Node]:
        result = parseAssignment()
        if isinstance(result, Error):
            return result
        if checkToken().type not in [
            TokenType.PERCENT_SCALE_OP,
            TokenType.MARKUP_OP,
            TokenType.MARKDOWN_OP,
        ]:
            return result
        left_node = result.ok_value()

        while checkToken().type in [
            TokenType.PERCENT_SCALE_OP,
            TokenType.MARKUP_OP,
            TokenType.MARKDOWN_OP,
        ]:
            token = checkToken()
            middle_node = Node(
                kind=NodeType.NUMANTICS_OPERATION,
                children=[],
                token=checkToken(),
                data=None,
            )
            if token.type == TokenType.PERCENT_SCALE_OP:
                result = expectNode(
                    TokenType.PERCENT_SCALE_OP,
                    "'*%' expected in numantics operation",
                    NodeType.PERCENT_SCALE_OPERATOR,
                )
                if isinstance(result, Error):
                    return result
                middle_node = result.ok_value()

            elif token.type == TokenType.MARKUP_OP:
                result = expectNode(
                    TokenType.MARKUP_OP,
                    "'+%' expected in numantics operation",
                    NodeType.MARKUP_OPERATOR,
                )
                if isinstance(result, Error):
                    return result
                middle_node = result.ok_value()

            elif token.type == TokenType.MARKDOWN_OP:
                result = expectNode(
                    TokenType.MARKDOWN_OP,
                    "'-%' expected in numantics operation",
                    NodeType.MARKDOWN_OPERATOR,
                )
                if isinstance(result, Error):
                    return result
                middle_node = result.ok_value()

            result = parseAssignment()
            if isinstance(result, Error):
                return result
            right_node = result.ok_value()

            left_node = Node(
                kind=NodeType.NUMANTICS_OPERATION,
                children=[left_node, middle_node, right_node],
                token=token,
                data=None,
            )
        return Ok(left_node)

    def parseAssignment() -> Result[Node, Node]:
        result = parseOrOperation()
        if isinstance(result, Error):
            return result

        token_type = checkToken().type
        if token_type not in [
            TokenType.ASSIGNMENT_OP,
            TokenType.PLUS_ASSIGNMENT_OP,
            TokenType.MINUS_ASSIGNMENT_OP,
            TokenType.MULTIPLY_ASSIGNMENT_OP,
            TokenType.DIVIDE_ASSIGNMENT_OP,
            TokenType.MODULO_ASSIGNMENT_OP,
        ]:
            return result
        node = Node(
            kind=NodeType.ASSIGNMENT_OP, children=[], token=checkToken(), data=None
        )
        node.children.append(result.ok_value())

        result = parseAssignmentOp()
        if isinstance(result, Error):
            return result
        node.children.append(result.ok_value())

        result = parseAssignment()
        if isinstance(result, Error):
            return result
        node.children.append(result.ok_value())

        return Ok(node)

    def parseAssignmentOp() -> Result[Node, Node]:
        token_type = checkToken().type
        if token_type == TokenType.ASSIGNMENT_OP:
            result = expectNode(
                TokenType.ASSIGNMENT_OP,
                "'=' expected in assignment operation",
                NodeType.ASSIGNMENT_OPERATOR,
            )
            return result
        elif token_type == TokenType.PLUS_ASSIGNMENT_OP:
            result = expectNode(
                TokenType.PLUS_ASSIGNMENT_OP,
                "'+=' expected in assignment operation",
                NodeType.PLUS_ASSIGNMENT_OPERATOR,
            )
            return result
        elif token_type == TokenType.MINUS_ASSIGNMENT_OP:
            result = expectNode(
                TokenType.MINUS_ASSIGNMENT_OP,
                "'-=' expected in assignment operation",
                NodeType.MINUS_ASSIGNMENT_OPERATOR,
            )
            return result
        elif token_type == TokenType.MULTIPLY_ASSIGNMENT_OP:
            result = expectNode(
                TokenType.MULTIPLY_ASSIGNMENT_OP,
                "'*=' expected in assignment operation",
                NodeType.MULTIPLY_ASSIGNMENT_OPERATOR,
            )
            return result
        elif token_type == TokenType.DIVIDE_ASSIGNMENT_OP:
            result = expectNode(
                TokenType.DIVIDE_ASSIGNMENT_OP,
                "'/=' expected in assignment operation",
                NodeType.DIVIDE_ASSIGNMENT_OPERATOR,
            )
            return result
        elif token_type == TokenType.MODULO_ASSIGNMENT_OP:
            result = expectNode(
                TokenType.MODULO_ASSIGNMENT_OP,
                "'%=' expected in assignment operation",
                NodeType.MODULO_ASSIGNMENT_OPERATOR,
            )
            return result
        else:
            return Error(errorFactory("Assignment operator expected"))

    def parseOrOperation() -> Result[Node, Node]:
        result = parseAndOperation()
        if isinstance(result, Error):
            return result
        if checkToken().type != TokenType.OR_OP:
            return result
        left_node = result.ok_value()

        while checkToken().type == TokenType.OR_OP:
            token = checkToken()

            result = expectNode(
                TokenType.OR_OP, "'||' expected in or operation", NodeType.OR_OPERATOR
            )
            if isinstance(result, Error):
                return result
            middle_node = result.ok_value()

            result = parseAssignment()
            if isinstance(result, Error):
                return result
            right_node = result.ok_value()

            left_node = Node(
                kind=NodeType.OR_OPERATION,
                children=[left_node, middle_node, right_node],
                token=token,
                data=None,
            )
        return Ok(left_node)

    def parseAndOperation() -> Result[Node, Node]:
        result = parseNotOperation()
        if isinstance(result, Error):
            return result
        if checkToken().type != TokenType.AND_OP:
            return result
        left_node = result.ok_value()

        while checkToken().type == TokenType.AND_OP:
            token = checkToken()

            result = expectNode(
                TokenType.AND_OP,
                "'&&' expected in and operation",
                NodeType.AND_OPERATOR,
            )
            if isinstance(result, Error):
                return result
            middle_node = result.ok_value()

            result = parseAssignment()
            if isinstance(result, Error):
                return result
            right_node = result.ok_value()

            left_node = Node(
                kind=NodeType.AND_OPERATION,
                children=[left_node, middle_node, right_node],
                token=token,
                data=None,
            )
        return Ok(left_node)

    def parseNotOperation() -> Result[Node, Node]:
        token = checkToken()
        if token.type == TokenType.NOT_OP:
            error = expect(TokenType.NOT_OP, "'!' expected in not operation")
            if error:
                return Error(error)

            result = parseNotOperation()
            if isinstance(result, Error):
                return result
            return Ok(
                Node(
                    kind=NodeType.NOT_OPERATION,
                    children=[result.ok_value()],
                    token=token,
                    data=None,
                )
            )
        else:
            result = parseRelation()
            return result

    def parseRelation() -> Result[Node, Node]:
        result = parseSum()
        if isinstance(result, Error):
            return result
        if checkToken().type not in [
            TokenType.OPEN_ANGLE_DELIMITER,
            TokenType.LESS_OR_EQUAL_OP,
            TokenType.CLOSED_ANGLE_DELIMITER,
            TokenType.GREATER_OR_EQUAL_OP,
            TokenType.NOT_EQUAL_OP,
            TokenType.EQUAL_OP,
        ]:
            return result
        left_node = result.ok_value()

        while checkToken().type in [
            TokenType.OPEN_ANGLE_DELIMITER,
            TokenType.LESS_OR_EQUAL_OP,
            TokenType.CLOSED_ANGLE_DELIMITER,
            TokenType.GREATER_OR_EQUAL_OP,
            TokenType.NOT_EQUAL_OP,
            TokenType.EQUAL_OP,
        ]:
            token = checkToken()

            result = parseRelationOp()
            if isinstance(result, Error):
                return result
            middle_node = result.ok_value()

            result = parseSum()
            if isinstance(result, Error):
                return result
            right_node = result.ok_value()

            left_node = Node(
                kind=NodeType.RELATION,
                children=[left_node, middle_node, right_node],
                token=token,
                data=None,
            )
        return Ok(left_node)

    def parseRelationOp() -> Result[Node, Node]:
        token_type = checkToken().type
        if token_type == TokenType.OPEN_ANGLE_DELIMITER:
            result = expectNode(
                TokenType.OPEN_ANGLE_DELIMITER,
                "'<' expected in relation",
                NodeType.LESS_OPERATOR,
            )
            return result
        elif token_type == TokenType.LESS_OR_EQUAL_OP:
            result = expectNode(
                TokenType.LESS_OR_EQUAL_OP,
                "'<=' expected in relation",
                NodeType.LESS_OR_EQUAL_OPERATOR,
            )
            return result
        elif token_type == TokenType.CLOSED_ANGLE_DELIMITER:
            result = expectNode(
                TokenType.CLOSED_ANGLE_DELIMITER,
                "'>' expected in relation",
                NodeType.GREATER_OPERATOR,
            )
            return result
        elif token_type == TokenType.GREATER_OR_EQUAL_OP:
            result = expectNode(
                TokenType.GREATER_OR_EQUAL_OP,
                "'>=' expected in relation",
                NodeType.GREATER_OR_EQUAL_OPERATOR,
            )
            return result
        elif token_type == TokenType.NOT_EQUAL_OP:
            result = expectNode(
                TokenType.NOT_EQUAL_OP,
                "'!=' expected in relation",
                NodeType.NOT_EQUAL_OPERATOR,
            )
            return result
        elif token_type == TokenType.EQUAL_OP:
            result = expectNode(
                TokenType.EQUAL_OP,
                "'==' expected in relation",
                NodeType.EQUAL_OPERATOR,
            )
            return result
        else:
            return Error(errorFactory("Relation operator expected"))

    def parseSum() -> Result[Node, Node]:
        result = parseTerm()
        if isinstance(result, Error):
            return result
        if checkToken().type not in [
            TokenType.PLUS_SYMBOL,
            TokenType.MINUS_SYMBOL,
        ]:
            return result
        left_node = result.ok_value()

        while checkToken().type in [
            TokenType.PLUS_SYMBOL,
            TokenType.MINUS_SYMBOL,
        ]:
            token = checkToken()

            middle_node = Node(
                kind=NodeType.SUM, children=[], token=checkToken(), data=None
            )

            if token.type == TokenType.PLUS_SYMBOL:
                result = expectNode(
                    TokenType.PLUS_SYMBOL, "'+' expected in sum", NodeType.ADD_OPERATOR
                )
                if isinstance(result, Error):
                    return result
                middle_node = result.ok_value()
            elif token.type == TokenType.MINUS_SYMBOL:
                result = expectNode(
                    TokenType.MINUS_SYMBOL, "'-' expected in sum", NodeType.SUB_OPERATOR
                )
                if isinstance(result, Error):
                    return result
                middle_node = result.ok_value()

            result = parseTerm()
            if isinstance(result, Error):
                return result
            right_node = result.ok_value()

            left_node = Node(
                kind=NodeType.SUM,
                children=[left_node, middle_node, right_node],
                token=token,
                data=None,
            )
        return Ok(left_node)

    def parseTerm() -> Result[Node, Node]:
        result = parseFactor()
        if isinstance(result, Error):
            return result
        if checkToken().type not in [
            TokenType.STAR_SYMBOL,
            TokenType.SLASH_SYMBOL,
            TokenType.PERCENT_SYMBOL,
        ]:
            return result
        left_node = result.ok_value()

        while checkToken().type in [
            TokenType.STAR_SYMBOL,
            TokenType.SLASH_SYMBOL,
            TokenType.PERCENT_SYMBOL,
        ]:
            token = checkToken()

            middle_node = Node(
                kind=NodeType.SUM, children=[], token=checkToken(), data=None
            )

            if token.type == TokenType.STAR_SYMBOL:
                result = expectNode(
                    TokenType.STAR_SYMBOL,
                    "'*' expected in term",
                    NodeType.MULT_OPERATOR,
                )
                if isinstance(result, Error):
                    return result
                middle_node = result.ok_value()
            elif token.type == TokenType.SLASH_SYMBOL:
                result = expectNode(
                    TokenType.SLASH_SYMBOL,
                    "'/' expected in term",
                    NodeType.DIV_OPERATOR,
                )
                if isinstance(result, Error):
                    return result
                middle_node = result.ok_value()
            elif token.type == TokenType.PERCENT_SYMBOL:
                result = expectNode(
                    TokenType.PERCENT_SYMBOL,
                    "'%' expected in term",
                    NodeType.MOD_OPERATOR,
                )
                if isinstance(result, Error):
                    return result
                middle_node = result.ok_value()

            result = parseFactor()
            if isinstance(result, Error):
                return result
            right_node = result.ok_value()

            left_node = Node(
                kind=NodeType.TERM,
                children=[left_node, middle_node, right_node],
                token=token,
                data=None,
            )
        return Ok(left_node)

    def parseFactor() -> Result[Node, Node]:
        if checkToken().type in [TokenType.PLUS_SYMBOL, TokenType.MINUS_SYMBOL]:
            node = Node(
                kind=NodeType.FACTOR, children=[], token=checkToken(), data=None
            )
            token = checkToken()
            if token.type == TokenType.PLUS_SYMBOL:
                result = expectNode(
                    TokenType.PLUS_SYMBOL,
                    "'+' expected in factor",
                    NodeType.POSITIVE_OPERATOR,
                )
                if isinstance(result, Error):
                    return result
                node.children.append(result.ok_value())
            elif token.type == TokenType.MINUS_SYMBOL:
                result = expectNode(
                    TokenType.MINUS_SYMBOL,
                    "'-' expected in factor",
                    NodeType.NEGATIVE_OPERATOR,
                )
                if isinstance(result, Error):
                    return result
                node.children.append(result.ok_value())
            result = parseFactor()
            if isinstance(result, Error):
                return result
            node.children.append(result.ok_value())
            return Ok(node)
        result = parsePower()
        return result

    def parsePower() -> Result[Node, Node]:
        node = Node(kind=NodeType.POWER, children=[], token=checkToken(), data=None)
        result = parsePrefix()
        if isinstance(result, Error):
            return result
        if checkToken().type != TokenType.CARET_SYMBOL:
            return result
        node.children.append(result.ok_value())

        error = expect(TokenType.CARET_SYMBOL, "'^' expected in power")
        if error:
            return Error(error)
        result = parsePower()
        if isinstance(result, Error):
            return result
        node.children.append(result.ok_value())

        return Ok(node)

    def parsePrefix() -> Result[Node, Node]:
        if checkToken().type in [TokenType.INCREMENT_OP, TokenType.DECREMENT_OP]:
            node = Node(
                kind=NodeType.PREFIX, children=[], token=checkToken(), data=None
            )
            token = checkToken()
            if token.type == TokenType.INCREMENT_OP:
                result = expectNode(
                    TokenType.INCREMENT_OP,
                    "'++' expected in prefix",
                    NodeType.PRE_INCREMENT_OPERATOR,
                )
                if isinstance(result, Error):
                    return result
                node.children.append(result.ok_value())
            elif token.type == TokenType.DECREMENT_OP:
                result = expectNode(
                    TokenType.DECREMENT_OP,
                    "'--' expected in prefix",
                    NodeType.PRE_DECREMENT_OPERATOR,
                )
                if isinstance(result, Error):
                    return result
                node.children.append(result.ok_value())
            result = parsePostfix()
            if isinstance(result, Error):
                return result
            node.children.append(result.ok_value())
            return Ok(node)
        result = parsePostfix()
        return result

    def parsePostfix() -> Result[Node, Node]:
        result = parsePrimary()
        if isinstance(result, Error):
            return result
        if checkToken().type not in [
            TokenType.INCREMENT_OP,
            TokenType.DECREMENT_OP,
            TokenType.OPEN_PARENTHESIS_DELIMITER,
            TokenType.CLOSED_SQUARE_DELIMITER,
        ]:
            return result
        left_node = result.ok_value()

        while checkToken().type in [
            TokenType.INCREMENT_OP,
            TokenType.DECREMENT_OP,
            TokenType.OPEN_PARENTHESIS_DELIMITER,
            TokenType.OPEN_SQUARE_DELIMITER,
        ]:
            token = checkToken()

            right_node = Node(
                kind=NodeType.POSTFIX, children=[], token=checkToken(), data=None
            )

            if token.type == TokenType.INCREMENT_OP:
                result = expectNode(
                    TokenType.INCREMENT_OP,
                    "'++' expected in postfix",
                    NodeType.POST_INCREMENT_OPERATOR,
                )
                if isinstance(result, Error):
                    return result
                right_node = result.ok_value()
            elif token.type == TokenType.DECREMENT_OP:
                result = expectNode(
                    TokenType.DECREMENT_OP,
                    "'--' expected in postfix",
                    NodeType.POST_DECREMENT_OPERATOR,
                )
                if isinstance(result, Error):
                    return result
                right_node = result.ok_value()
            elif token.type == TokenType.OPEN_PARENTHESIS_DELIMITER:
                error = expect(
                    TokenType.OPEN_PARENTHESIS_DELIMITER,
                    "'(' expected in postfix",
                )
                if error:
                    return Error(error)
                result = parseArguments()
                if isinstance(result, Error):
                    return result
                error = expect(
                    TokenType.CLOSED_PARENTHESIS_DELIMITER,
                    "')' expected in postfix",
                )
                right_node = result.ok_value()
            elif token.type == TokenType.OPEN_SQUARE_DELIMITER:
                error = expect(
                    TokenType.OPEN_SQUARE_DELIMITER,
                    "'[' expected in postfix",
                )
                if error:
                    return Error(error)
                result = parseExpression()
                if isinstance(result, Error):
                    return result
                error = expect(
                    TokenType.CLOSED_SQUARE_DELIMITER,
                    "']' expected in postfix",
                )
                right_node = result.ok_value()

            left_node = Node(
                kind=NodeType.POSTFIX,
                children=[left_node, right_node],
                token=token,
                data=None,
            )
        return Ok(left_node)

    def parseArguments() -> Result[Node, Node]:
        node = Node(kind=NodeType.ARGUMENTS, children=[], token=checkToken(), data=None)
        if checkToken().type == TokenType.CLOSED_PARENTHESIS_DELIMITER:
            return Ok(node)
        result = parseExpression()
        if isinstance(result, Error):
            return result
        node.children.append(result.ok_value())

        while checkToken().type == TokenType.COMMA_DELIMITER:
            error = expect(TokenType.COMMA_DELIMITER, "',' expected in parameter list")
            if error:
                return Error(error)
            result = parseExpression()
            if isinstance(result, Error):
                return result
            node.children.append(result.ok_value())

        return Ok(node)

    def parsePrimary() -> Result[Node, Node]:
        if checkToken().type == TokenType.OPEN_PARENTHESIS_DELIMITER:
            node = Node(
                kind=NodeType.PRIMARY, children=[], token=checkToken(), data=None
            )
            error = expect(
                TokenType.OPEN_PARENTHESIS_DELIMITER, "'(' expected in primary"
            )
            if error:
                return Error(error)
            result = parseExpression()
            if isinstance(result, Error):
                return result
            node.children.append(result.ok_value())
            error = expect(
                TokenType.CLOSED_PARENTHESIS_DELIMITER, "')' expected in primary"
            )
            return Ok(node)
        return parseAtom()

    def parseAtom() -> Result[Node, Node]:
        token = checkToken()
        if token.type == TokenType.IDENTIFIER:
            result = expectNode(
                TokenType.IDENTIFIER, "identifier expected in atom", NodeType.IDENTIFIER
            )
            return result
        elif token.type == TokenType.TRUE_LITERAL:
            result = expectNode(
                TokenType.TRUE_LITERAL,
                "true literal expected in atom",
                NodeType.TRUE_LITERAL,
            )
            return result
        elif token.type == TokenType.FALSE_LITERAL:
            result = expectNode(
                TokenType.FALSE_LITERAL,
                "false literal expected in atom",
                NodeType.FALSE_LITERAL,
            )
            return result
        elif token.type == TokenType.INT_LITERAL:
            result = expectNode(
                TokenType.INT_LITERAL,
                "int literal expected in atom",
                NodeType.INT_LITERAL,
            )
            return result
        elif token.type == TokenType.FLOAT_LITERAL:
            result = expectNode(
                TokenType.FLOAT_LITERAL,
                "float literal expected in atom",
                NodeType.FLOAT_LITERAL,
            )
            return result
        elif token.type == TokenType.CHAR_LITERAL:
            result = expectNode(
                TokenType.CHAR_LITERAL,
                "char literal expected in atom",
                NodeType.CHAR_LITERAL,
            )
            return result
        elif token.type == TokenType.STRING_LITERAL:
            result = expectNode(
                TokenType.STRING_LITERAL,
                "string literal expected in atom",
                NodeType.STRING_LITERAL,
            )
            return result
        else:
            return Error(errorFactory("value expected"))

    def parseStatement() -> Result[Node, Node]:
        node = Node(NodeType.STATEMENT, children=[], token=checkToken(), data=None)
        token_type = checkToken().type

        def recoverStatement(result: Error[Node]):
            old_index = token_index
            recoverError(
                [
                    TokenType.IF_STATEMENT,
                    TokenType.SWITCH_STATEMENT,
                    TokenType.SWEEP_STATEMENT,
                    TokenType.WHILE_LOOP,
                    TokenType.FUNC_STATEMENT,
                    TokenType.FOR_LOOP,
                    TokenType.VOID_TYPE,
                    TokenType.INT_TYPE,
                    TokenType.FLOAT_TYPE,
                    TokenType.BOOL_TYPE,
                    TokenType.CHAR_TYPE,
                    TokenType.STRING_TYPE,
                    TokenType.OPEN_CURLY_DELIMITER,
                    TokenType.NEXT_STATEMENT,
                    TokenType.STOP_STATEMENT,
                    TokenType.RETURN_STATEMENT,
                    TokenType.SEMI_COLON_DELIMITER,
                    TokenType.CLOSED_CURLY_DELIMITER,
                ]
            )
            if token_index == old_index:
                nextToken()
            node.children.append(result.error_value())

        if token_type == TokenType.IF_STATEMENT:
            result = parseIfStmt()
            if isinstance(result, Error):
                recoverStatement(result)
            else:
                node.children.append(result.ok_value())
        elif token_type == TokenType.SWITCH_STATEMENT:
            result = parseSwitchStmt()
            if isinstance(result, Error):
                recoverStatement(result)
            else:
                node.children.append(result.ok_value())
        elif token_type == TokenType.SWEEP_STATEMENT:
            result = parseSweepStmt()
            if isinstance(result, Error):
                recoverStatement(result)
            else:
                node.children.append(result.ok_value())
        elif token_type == TokenType.WHILE_LOOP:
            result = parseWhileStmt()
            if isinstance(result, Error):
                recoverStatement(result)
            else:
                node.children.append(result.ok_value())
        elif token_type == TokenType.FUNC_STATEMENT:
            result = parseFunctionStmt()
            if isinstance(result, Error):
                recoverStatement(result)
            else:
                node.children.append(result.ok_value())
        elif token_type == TokenType.FOR_LOOP:
            result = parseForStmt()
            if isinstance(result, Error):
                recoverStatement(result)
            else:
                node.children.append(result.ok_value())
        elif token_type in [
            TokenType.VOID_TYPE,
            TokenType.INT_TYPE,
            TokenType.FLOAT_TYPE,
            TokenType.BOOL_TYPE,
            TokenType.CHAR_TYPE,
            TokenType.STRING_TYPE,
        ]:
            result = parseDeclarationStmt()
            if isinstance(result, Error):
                recoverStatement(result)
            else:
                node.children.append(result.ok_value())
        elif token_type == TokenType.OPEN_CURLY_DELIMITER:
            result = parseBlock()
            if isinstance(result, Error):
                recoverStatement(result)
            else:
                node.children.append(result.ok_value())
        elif token_type == TokenType.NEXT_STATEMENT:
            result = parseNextStmt()
            if isinstance(result, Error):
                recoverStatement(result)
            else:
                node.children.append(result.ok_value())
        elif token_type == TokenType.STOP_STATEMENT:
            result = parseStopStmt()
            if isinstance(result, Error):
                recoverStatement(result)
            else:
                node.children.append(result.ok_value())
        elif token_type == TokenType.RETURN_STATEMENT:
            result = parseReturnStmt()
            if isinstance(result, Error):
                recoverStatement(result)
            else:
                node.children.append(result.ok_value())
        else:
            result = parseExpressionStmt()
            if isinstance(result, Error):
                recoverStatement(result)
            else:
                node.children.append(result.ok_value())

        return Ok(node)

    def parseBlock() -> Result[Node, Node]:
        node = Node(NodeType.BLOCK, children=[], token=checkToken(), data=None)
        error = expect(TokenType.OPEN_CURLY_DELIMITER, "'{' expected in block")
        if error:
            return Error(error)
        while True:
            type = checkToken().type
            if type == TokenType.CLOSED_CURLY_DELIMITER:
                break
            if type == TokenType.ENDMARKER:
                node.children.append(errorFactory("block unterminated"))
                return Ok(node)

            result = parseStatement()
            if isinstance(result, Error):
                old_index = token_index
                recoverError(
                    [TokenType.SEMI_COLON_DELIMITER, TokenType.CLOSED_CURLY_DELIMITER]
                )
                if token_index == old_index:
                    nextToken()
                node.children.append(result.error_value())
            else:
                node.children.append(result.ok_value())

        error = expect(TokenType.CLOSED_CURLY_DELIMITER, "'}' expected in block")
        if error:
            return Error(error)
        return Ok(node)

    def parseFunctionStmt() -> Result[Node, Node]:
        node = Node(
            kind=NodeType.FUNCTION_STMT, children=[], token=checkToken(), data=None
        )

        def recoverFunctionStmt(result: Error[Node]):
            old_index = token_index
            recoverErrorNonConsuming(
                [
                    TokenType.OPEN_CURLY_DELIMITER,
                ]
            )
            if token_index == old_index:
                nextToken()
            node.children.append(result.error_value())

            if checkToken().type == TokenType.OPEN_CURLY_DELIMITER:
                new_result = parseBlock()
                if isinstance(new_result, Error):
                    return new_result
                node.children.append(new_result.ok_value())
                return Ok(node)

            return Error(node)

        error = expect(TokenType.FUNC_STATEMENT, "'func' expected in function")
        if error:
            recoverFunctionStmt(Error(error))

        result = expectNode(
            TokenType.IDENTIFIER, "Function name expected", NodeType.IDENTIFIER
        )
        if isinstance(result, Error):
            return result
        node.children.append(result.ok_value())

        error = expect(TokenType.OPEN_PARENTHESIS_DELIMITER, "'(' expected in function")
        if error:
            return recoverFunctionStmt(Error(error))

        if current_token.type != TokenType.VERTICAL_BAR_DELIMITER:
            result = parseParameterList()
            if isinstance(result, Error):
                return recoverFunctionStmt(result)
            node.children.append(result.ok_value())
        else:
            node.children.append(
                Node(
                    NodeType.PARAMETER_LIST, children=[], token=checkToken(), data=None
                )
            )

        error = expect(TokenType.VERTICAL_BAR_DELIMITER, "'|' expected in function")
        if error:
            return recoverFunctionStmt(Error(error))

        result = parseType()
        if isinstance(result, Error):
            return recoverFunctionStmt(result)
        node.children.append(result.ok_value())

        error = expectNonConsuming(
            TokenType.CLOSED_PARENTHESIS_DELIMITER, "')' expected in function"
        )
        if error:
            return recoverFunctionStmt(Error(error))
        nextToken()

        result = parseBlock()
        if isinstance(result, Error):
            return recoverFunctionStmt(result)
        node.children.append(result.ok_value())

        return Ok(node)

    def parseExternalDeclaration() -> Result[Node, Node]:
        if checkToken().type == TokenType.FUNC_STATEMENT:
            return parseFunctionStmt()
        else:
            return parseDeclarationStmt()

    file_node = Node(kind=NodeType.FILE, children=[], token=tokens[0], data=None)

    while current_token.type != TokenType.ENDMARKER:
        result = parseExternalDeclaration()
        if isinstance(result, Ok):
            file_node.children.append(result.ok_value())
        else:
            file_node.children.append(result.error_value())
            old_index = token_index
            recoverErrorNonConsuming(
                [
                    TokenType.FUNC_STATEMENT,
                    TokenType.VOID_TYPE,
                    TokenType.INT_TYPE,
                    TokenType.FLOAT_TYPE,
                    TokenType.BOOL_TYPE,
                    TokenType.CHAR_TYPE,
                    TokenType.STRING_TYPE,
                ]
            )
            if token_index == old_index:
                nextToken()

    return file_node, has_error
