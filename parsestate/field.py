# -*- coding: utf-8 -*-

from ..tokentype import TokenType
from .state import ParseState

class FieldState(ParseState):

	def __init__(self, parser):

		super().__init__(parser)
		self._parser._setStateValue('inField', True, False)

		# Initialize the two components of a field
		self.__fldRslt = ''
		self.__fldInst = ''

	###########################################################################

	# Append the contents of a \field group to the current paragraph.
	def __append(self):

		# We let the callback handle it
		callback = self._parser._getCallback('onField')
		if callback:
			callback(self._parser, self.__fldinst, self.__fldrslt)

		# There's no callback that knows how to handle it, so we'll just do things
		# the dumb way by appending the \fldrslt value to the current paragraph.
		else:
			self._parser._appendToCurrentParagraph(self.__fldrslt)

	###########################################################################

	# Look out for when we've finished with the field group.
	def _parseCloseBrace(self):

		super()._parseCloseBrace(False)

		# Once we've finished with the field group, we can stop parsing in this
		# state.
		if 'inField' not in self._parser.fullState:
			self.__append()
			return False
		else:
			return True

	###########################################################################

	def _parseControl(self, word, param):

		# If we're parsing a \fldinst value and encounter another control word
		# with the \* prefix, we know we're done parsing the parts of \fldinst
		# we care about (this will change as I handle more of the RTF spec.)
		if '\\*' == word and 'inFieldinst' in self._parser.curState and self._parser.curState['inFieldinst']:
			self._parser._setStateValue('inFieldinst', False, False)
			return True

		# Most recent calculated result of field. In practice, this is also
		# the text that would be parsed into the paragraph by an RTF reader
		# that doesn't understand fields.
		elif TokenType.OPEN_BRACE == self._parser._prevToken[0] and '\\fldrslt' == word:
			self._parser._setStateValue('inFieldrslt', True, False)
			return True

		# Field instruction
		elif '\\*' == self._parser._prevToken[1] and '\\fldinst' == word:
			self._parser._setStateValue('inFieldinst', True, False)
			return True

		else:
			return super()._parseControl(word, param)

	###########################################################################

	def _parseCharacter(self, token):

		if 'inFieldrslt' in self._parser.fullState and self._parser.fullState['inFieldrslt']:
			self.__fldRslt += token

		elif 'inFieldinst' in self._parser.fullState and self._parser.fullState['inFieldinst']:
			self.self.__fldInst += token

		return True

