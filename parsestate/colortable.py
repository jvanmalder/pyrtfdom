# -*- coding: utf-8 -*-

from ..tokentype import TokenType
from .state import ParseState

DEFAULT_TINT  = 255
DEFAULT_SHADE = 255

class ColorTableState(ParseState):

	def __init__(self, parser):

		super().__init__(parser)
		self._parser._setStateValue('private', 'colorTable', True)

		self.__curColor = {'tint': DEFAULT_TINT, 'shade': DEFAULT_SHADE}
		self.__colorParsed = False # True every time we parse a new color

	###########################################################################

	# Inserts the current color into the parser's color table.
	def __insertCurColor(self):

		if self.__colorParsed:
			self._parser._insertColor(self.__curColor)
			self.__curColor = {}
			self.__colorParsed = False
		else:
			self._parser._insertColor(False)

	###########################################################################

	def _parseCloseBrace(self):

		super()._parseCloseBrace(False)

		# We shouldn't have nested braces inside the color table, but making it
		# possible to skip over them if they're encountered will make the parser
		# more robust in the case of a malformatted document.
		if 'colorTable' not in self._parser._fullState['private']:
			return False
		else:
			return True

	###########################################################################

	def _parseControl(self, word, param):

		validWords = ['red', 'green', 'blue', 'tint', 'shade']

		word = word[1:]
		if isinstance(param, str) and param.isdigit():
			param = int(param)
		else:
			param = None

		if word in validWords:
			self.__colorParsed = True
			self.__curColor[word] = param

		return True

	###########################################################################

	# Do nothing...
	def _parseCharacter(self, token):

		if ';' == token:
			self.__insertCurColor()

		return True

