import ast

def try_eval(val):
    try:
        val = ast.literal_eval(val)
    except (ValueError, SyntaxError):
        #evaluation failed, so we most likely have a string
        pass
    return val
