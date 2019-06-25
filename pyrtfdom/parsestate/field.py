# -*- coding: utf-8 -*-

from ..tokentype import TokenType
from .state import ParseState

class FieldState(ParseState):

	def __init__(self, parser):

		super().__init__(parser)
		self._parser._setStateValue('private', 'inField', True)

		# Initialize the two components of a field
		self.__fldRslt = ''
		self.__fldInst = ''

	###########################################################################

	# Append the contents of a \field group to the current paragraph.
	def __append(self):

		# We let the callback handle it
		callback = self._parser._getCallback('onField')
		if callback:
			callback(self._parser, self.__fldInst, self.__fldRslt)

		# There's no callback that knows how to handle it, so we'll just do things
		# the dumb way by appending the \fldrslt value to the current paragraph.
		else:
			self._parser._appendToCurrentParagraph(self.__fldRslt)

	###########################################################################

	# Look out for when we've finished with the field group.
	def _parseCloseBrace(self):

		super()._parseCloseBrace(False)

		# Once we've finished with the field group, we can stop parsing in this
		# state.
		if 'inField' not in self._parser._fullState['private']:
			self.__append()
			return False
		else:
			return True

	###########################################################################

	def _parseControl(self, word, param):

		# If we're parsing a \fldinst value and encounter another control word
		# with the \* prefix, we know we're done parsing the parts of \fldinst
		# we care about (this will change as I handle more of the RTF spec.)
		if '\\*' == word and 'inFieldinst' in self._parser._curState['private'] and self._parser._curState['private']['inFieldinst']:
			self._parser._setStateValue('private', 'inFieldinst', False)
			return True

		# Most recent calculated result of field. In practice, this is also
		# the text that would be parsed into the paragraph by an RTF reader
		# that doesn't understand fields.
		elif TokenType.OPEN_BRACE == self._parser._prevToken[0] and '\\fldrslt' == word:
			self._parser._setStateValue('private', 'inFieldrslt', True)
			return True

		# Field instruction
		elif '\\*' == self._parser._prevToken[1] and '\\fldinst' == word:
			self._parser._setStateValue('private', 'inFieldinst', True)
			return True

		else:
			return super()._parseControl(word, param)

	###########################################################################

	def _parseCharacter(self, token):

		if 'inFieldrslt' in self._parser._fullState['private'] and self._parser._fullState['private']['inFieldrslt']:
			self.__fldRslt += token

		elif 'inFieldinst' in self._parser._fullState['private'] and self._parser._fullState['private']['inFieldinst']:
			self.__fldInst += token

		return True

