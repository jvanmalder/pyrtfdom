# -*- coding: utf-8 -*-

class FieldState(ParseState):

	def __init__(self, parser):

		self.parser._setStateValue('inField', True, False)

		# Initialize the two components of a field
		self.__fldRslt = ''
		self.__fldInst = ''

		super().__init__(parser)

	###########################################################################

	# Append the contents of a \field group to the current paragraph.
	def __append(self):

		# We let the callback handle it
		# TODO: make data-protected-safe way to call this callback
		if 'onField' in self.__options['callbacks']:
			self.parser.__options['callbacks']['onField'](self.parser, self.__fldinst, self.__fldrslt)

		# There's no callback that knows how to handle it, so we'll just do things
		# the dumb way by appending the \fldrslt value to the current paragraph.
		else:
			self.parser._appendToCurrentParagraph(self.__fldrslt)

	###########################################################################

	# Look out for when we've finished with the field group.
	def _parseCloseBrace(self):

		super()._parseCloseBrace(False)

		# Once we've finished with the field group, we can stop parsing in this
		# state.
		if 'inField' not in self.parser.fullState:
			self.__append()
			return False
		else:
			return True

	###########################################################################

	def _parseControl(self, word, param):

		# If we're parsing a \fldinst value and encounter another control word
		# with the \* prefix, we know we're done parsing the parts of \fldinst
		# we care about (this will change as I handle more of the RTF spec.)
		if '\\*' == word and 'inFieldinst' in self.__curState and self.__curState['inFieldinst']:
			self.parser._setStateValue('inFieldinst', False, False)
			return True

		# Most recent calculated result of field. In practice, this is also
		# the text that would be parsed into the paragraph by an RTF reader
		# that doesn't understand fields.
		elif TokenType.OPEN_BRACE == self.parser._prevToken[0] and '\\fldrslt' == word:
			self.parser._setStateValue('inFieldrslt', True, False)
			return True

		# Field instruction
		elif '\\*' == self.parser._prevToken[1] and '\\fldinst' == word:
			self.parser._setStateValue('inFieldinst', True, False)
			return True

		else:
			return super()._parseControl(word, param)

	###########################################################################

	def _parseCharacter(self, token):

		if 'inFieldrslt' in self.parser.fullState and self.parser.fullState['inFieldrslt']:
			self.__fldRslt += token

		elif 'inFieldinst' in self.parser.fullState and self.parser.fullState['inFieldinst']:
			self.self.__fldInst += token

