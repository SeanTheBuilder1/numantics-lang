import sys
import json

from ast_converter import convertCstToAst
from lexer_analyzer import analyzeSource
from lexer_token import Token, TokenType
from semantic_analyzer import resolveFile
from syntax_analyzer import parseFile
from line_starts import build_line_starts, index_to_line_col_batch


def main():
    if len(sys.argv) < 2:
        print("Usage:", sys.argv[0], "[file] [optional: save file]")
        return
    file = open(sys.argv[1], "r")
    code = file.read()
    code = code.replace("\r\n", "\n")
    code = code.replace("\n\r", "\n")
    code = code.replace("\r", "\n")
    tokens = analyzeSource(code)
    token_list = []
    line_starts = build_line_starts(code)
    for t in tokens:
        start_line, start_col = index_to_line_col_batch(t.start, line_starts)
        end_line, end_col = index_to_line_col_batch(t.end, line_starts)
        token_list.append(
            {
                "type": str(t.type.name),
                "start": int(t.start),
                "end": int(t.end),
                "start_line": start_line,
                "start_col": start_col,
                "end_line": end_line,
                "end_col": end_col,
                "lexeme": code[t.start : t.end],
            }
        )
    # print(tokens)
    file.close()
    if len(sys.argv) >= 3:
        with open(sys.argv[2], "w") as f:
            json.dump(token_list, f, indent=2)

    def filterTokens(token: Token):
        return not (
            token.type == TokenType.WHITESPACE
            or token.type == TokenType.NEWLINE
            or token.type == TokenType.COMMENT
        )

    tokens = list(filter(filterTokens, tokens))
    result, has_error = parseFile(tokens)
    if has_error:
        # print(result.pretty(code, line_starts, 4))
        print(result.errors(code, line_starts))
        sys.exit(1)
    else:
        print(result.pretty(code, line_starts, 4))
        ast = convertCstToAst(result)
        symbols, has_semantic_error = resolveFile(ast, code)


if __name__ == "__main__":
    main()
