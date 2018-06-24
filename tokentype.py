# -*- coding: utf-8 -*-

from enum import Enum

# Token types
class TokenType(Enum):
	OPEN_BRACE        = 1
	CLOSE_BRACE       = 2
	CONTROL_WORDORSYM = 3
	CHARACTER         = 4
	EOF               = 5

