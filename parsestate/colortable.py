# -*- coding: utf-8 -*-

from ..tokentype import TokenType
from .state import ParseState

class ColorTableState(ParseState):

	def __init__(self, parser):

		super().__init__(parser)
		self._parser._setStateValue('private', 'colorTable', True)

	###########################################################################

	def _parseCloseBrace(self):

		super()._parseCloseBrace(False)

		if 'colorTable' not in self._parser._fullState['private']:
			return False
		else:
			# TODO: add color
			return True

	###########################################################################

	def _parseControl(self, word, param):

		# TODO
		return True

	###########################################################################

	# Do nothing...
	def _parseCharacter(self, token):

		# TODO
		return True

