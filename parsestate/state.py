# -*- coding: utf-8 -*-

import re, time
from abc import ABCMeta, abstractmethod

from ..parse import TokenType

# The parser is modeled loosely on a state machine. When we parse different
# kinds of groups, we're going to enter different states. The main body of the
# document is considered one state, and is the default state we enter when we
# begin parsing.
class ParseState(object):

	def __init__(self, parser):

		self._parser = parser

	###########################################################################

	# Splits a control word token into its word and parameter parts. Returns an
	# array of the form [word, parameter]. If there's no parameter, that part of
	# the array will be set to None.
	def __splitControlWord(self, token):

		control = token[1].strip()

		paramSearch = re.search('-?\d+', control)
		if paramSearch:
			paramStartIndex = paramSearch.start()
			word = control[0:paramStartIndex]
			param = control[paramStartIndex:]
		else:
			word = control
			param = None

		return [word, param]

	###########################################################################

	# Get the control word or symbol at the current position
	def _getControlWordOrSymbol(self):

		token = '\\'

		if not self.parser._content[self.parser._curPos].isalpha() and not self.parser._content[self.parser._curPos].isspace():

			# Character represented in \'xx form (if no hexadecimal digit
			# follows, it will be the responsibility of the parser to treat it
			# as an unsupported control symbol.)
			if "'" == self.parser._content[self.parser._curPos]:
				token = token + self.parser._content[self.parser._curPos]
				self.parser._curPos = self.parser._curPos + 1
				decimalCount = 0
				while decimalCount < 2 and (
					self.parser._content[self.parser._curPos].isdigit() or
					self.parser._content[self.parser._curPos].upper() in ['A', 'B', 'C', 'D', 'E']
				):
					token = token + self.parser._content[self.parser._curPos]
					self.parser._curPos = self.parser._curPos + 1
					decimalCount += 1

			# Control symbol
			else:
				token = token + self.parser._content[self.parser._curPos]
				self.parser._curPos = self.parser._curPos + 1

		# Control word
		elif self.parser._content[self.parser._curPos].isalpha():

			while self.parser._content[self.parser._curPos].isalpha():
				token = token + self.parser._content[self.parser._curPos]
				self.parser._curPos = self.parser._curPos + 1

			# Control word has a numeric parameter
			digitIndex = self.parser._curPos
			if self.parser._content[self.parser._curPos].isdigit() or '-' == self.parser._content[self.parser._curPos]:
				while self.parser._content[self.parser._curPos].isdigit() or (self.parser._curPos == digitIndex and '-' == self.parser._content[self.parser._curPos]):
					token = token + self.parser._content[self.parser._curPos]
					self.parser._curPos = self.parser._curPos + 1

			# If there's a single space that serves as a delimiter, the spec says
			# we should append it to the control word.
			if self.parser._content[self.parser._curPos].isspace():
				token = token + self.parser._content[self.parser._curPos]
				self.parser._curPos = self.parser._curPos + 1

		else:
			raise ValueError("Encountered unescaped '\\'")

		return token

	###########################################################################

	# Get next token from the currently loaded RTF
	def _getNextToken(self):

		# We haven't opened an RTF yet
		if not self.parser._content:
			return False

		# We've reached the end of the file
		elif self.parser._curPos >= len(self.parser._content):
			return [TokenType.EOF, '']

		# Control words and their parameters count as single tokens
		elif '\\' == self.parser._content[self.parser._curPos]:
			self.parser._curPos = self.parser._curPos + 1
			return [TokenType.CONTROL_WORDORSYM, self._getControlWordOrSymbol()]

		# Covers '{', '}' and any other character
		else:

			tokenType = TokenType.CHARACTER

			if '{' == self.parser._content[self.parser._curPos]:
				tokenType = TokenType.OPEN_BRACE
			elif '}' == self.parser._content[self.parser._curPos]:
				tokenType = TokenType.CLOSE_BRACE

			self.parser._curPos = self.parser._curPos + 1
			return [tokenType, self.parser._content[self.parser._curPos - 1]]

	###########################################################################

	# Defines what we should do when we encounter an open brace token. By
	# default, we just push the current state onto the stack and create a new
	# local copy. If a particular parsing state requires us to handle this
	# token differently, then its class should override this method. If we
	# return false instead of true, it means we should return from the current
	# call to self.parse().
	def _parseOpenBrace(self):

		self.parser._pushStateStack()
		return True

	###########################################################################

	# Defines what we should do when we encounter a close brace token. By
	# default, we just pop the current state off the stack and return to the
	# previous state. If a particular parsing state needs to handle this token
	# differently, then its class should override this method. If
	# callOnStateChange is set to true, we call the onStateChange callback
	# (this is the default.) If we return false instead of true, it means we
	# should return from the current call to self.parse().
	def _parseCloseBrace(self, callOnStateChange = True):

		oldStateCopy = self.parser.curState
		oldStateFull = self.parser.fullState # used in call to onStateChange
		self.parser._popStateStack()

		#: TODO: factor out this callback call and give it proper data protections
		if callOnStateChange and 'onStateChange' in self.__options['callbacks']:
			self.parser.__options['callbacks']['onStateChange'](self.parser, oldStateFull, self.parser.fullState)

		return True

	###########################################################################

	# Executes a control word or symbol. This defines default behavior for all
	# parser states. If the control words here need to have their behavior
	# changed, or if new control words need to be defined, this method should
	# be overridden. If we return false instead of true, it means we should
	# return from the current call to self.parse().
	def _parseControl(self, word, param):

		################################################
		#          Escaped special characters          #
		################################################

		elif '\\\\' == word:
			self.parser._appendToCurrentParagraph('\\')

		elif '\\{' == word:
			self.parser._appendToCurrentParagraph('{')

		elif '\\}' == word:
			self.parser._appendToCurrentParagraph('}')

		################################################
		#     Unicode and other special Characters     #
		################################################

		# Non-breaking space
		elif '\\~' == word:
			self.parser._appendToCurrentParagraph('\N{NO-BREAK SPACE}')

		# Non-breaking hyphen
		elif '\\_' == word:
			self.parser._appendToCurrentParagraph('\N{NON-BREAKING HYPHEN}')

		# A space character with the width of the letter 'm' in the current font
		elif '\\emspace' == word:
			self.parser._appendToCurrentParagraph('\N{EM SPACE}')

		# A space character with the width of the letter 'n' in the current font
		elif '\\enspace' == word:
			self.parser._appendToCurrentParagraph('\N{EN SPACE}')

		# En dash
		elif '\\endash' == word:
			self.parser._appendToCurrentParagraph('\N{EN DASH}')

		# Em dash
		elif '\\emdash' == word:
			self.parser._appendToCurrentParagraph('\N{EM DASH}')

		# Left single quote
		elif '\\lquote' == word:
			self.parser._appendToCurrentParagraph('\N{LEFT SINGLE QUOTATION MARK}')

		# Right single quote
		elif '\\rquote' == word:
			self.parser._appendToCurrentParagraph('\N{RIGHT SINGLE QUOTATION MARK}')

		# Left double quote
		elif '\\ldblquote' == word:
			self.parser._appendToCurrentParagraph('\N{LEFT DOUBLE QUOTATION MARK}')

		# Right double quote
		elif '\\rdblquote' == word:
			self.parser._appendToCurrentParagraph('\N{RIGHT DOUBLE QUOTATION MARK}')

		# Non-paragraph-breaking line break
		elif '\\line' == word:
			self.parser._appendToCurrentParagraph('\n')

		# Tab character
		elif '\\tab' == word:
			self.parser._appendToCurrentParagraph('\t')

		# tab
		elif '\\bullet' == word:
			self.parser._appendToCurrentParagraph('\N{BULLET}')

		# Current date (long form)
		elif '\\chdate' == word or '\\chdpl' == word:
			self.parser._appendToCurrentParagraph(time.strftime("%A, %B %d, %Y"))

		# Current date (abbreviated form)
		elif '\\chdpa' == word:
			self.parser._appendToCurrentParagraph(time.strftime("%m/%d/%Y"))

		# Current date (abbreviated form)
		elif '\\chtime' == word:
			self.parser._appendToCurrentParagraph(time.strftime("%I:%M:%S %p"))

		# A character of the form \uXXX to be added to the current paragraph.
		# Unlike \'XX, \u takes a decimal number instead of hex.
		elif '\\u' == word and param:
			try:
				self.parser._appendToCurrentParagraph(chr(int(param, 10)))
			except ValueError:
				return

		# A character of the form \'XX to be added to the current paragraph
		elif "\\'" == word and param:

			try:

				charCode = int(param, 16)
				prevTokenParts = self.__splitControlWord(self.parser._prevToken)

				# Per the RTF standard, if a \uXXX unicode symbol has an ANSI
				# equivalent, the ANSI character will be encoded directly
				# following \uXXX in the form \'XX. This is for backward
				# compatibility with older RTF readers. Whenever we encounter
				# \'XX directly after \uXXX, therefore, we'll ignore it. Also,
				# \'XX can only have a maximum value of 255 (FF.) Since my
				# tokenizer doesn't detect this and might pick up extra digits,
				# we do a bounds check here and ignore the character if it falls
				# out of bounds.
				if '\\u' != prevTokenParts[0] and charCode <= 255:
					self.parser._appendToCurrentParagraph(chr(charCode))

			except ValueError:
				return

		################################################
		#        Misc control words and symbols        #
		################################################

		# We're inserting a page break into the current paragraph
		elif '\\page' == word or '\\pagebb' == word:
			self._breakPage()

		# We're ending the current paragraph and starting a new one
		elif '\\par' == word:
			self._closeParagraph()
			self._openParagraph()

		# Reset all styling to an off position in the current state
		elif '\\plain' == word:
			self._resetStateFormattingAttributes()

		# Paragraph alignment
		elif '\\ql' == word:
			self.parser._setStateValue('alignment', 'left')

		elif '\\qr' == word:
			self.parser._setStateValue('alignment', 'right')

		elif '\\qc' == word:
			self.parser._setStateValue('alignment', 'center')

		elif '\\qd' == word:
			self.parser._setStateValue('alignment', 'distributed')

		elif '\\qj' == word:
			self.parser._setStateValue('alignment', 'justified')

		elif '\\qt' == word:
			self.parser._setStateValue('alignment', 'thai-distributed')

		# TODO: how do I want to handle \qkN alignment? Will require setting
		# two attributes.

		# Italic
		elif '\\i' == word:
			if param is None or '1' == param:
				self.parser._setStateValue('italic', True)
			else:
				self.parser._setStateValue('italic', False)

		# Bold
		elif '\\b' == word:
			if param is None or '1' == param:
				self.parser._setStateValue('bold', True)
			else:
				self.parser._setStateValue('bold', False)

		# Underline
		elif '\\ul' == word:
			if param is None or '1' == param:
				self.parser._setStateValue('underline', True)
			else:
				self.parser._setStateValue('underline', False)

		# Strike-through
		elif '\\strike' == word:
			if param is None or '1' == param:
				self.parser._setStateValue('strikethrough', True)
			else:
				self.parser._setStateValue('strikethrough', False)

		return True

	###########################################################################

	# Defines what we should do when we encounter an ordinary character token.
	# If function returns false instead of true, it means we should return from
	# the current call to self.parse().
	@abstractmethod
	def _parseCharacter(self, token):
		pass

	###########################################################################

	# Parse the RTF and return an array of formatted paragraphs.
	def parse(self):

		if self.parser._content:

			self.parser._curToken = self._getNextToken()
			self.parser._prevToken = False

			# Start with a default state where all the formatting attributes are
			# turned off.
			self._initState()

			# Open our initial paragraph
			self._openParagraph()

			# If this gets set to true, it means we're inside a nested call
			# to parse and that we've been told to return.
			returnFromCall = False

			while !returnFromCall and TokenType.EOF != self.parser._curToken[0]:

				if TokenType.OPEN_BRACE == self.parser._curToken[0]:
					if (!self._parseOpenBrace()):
						returnFromCall = True

				# Restore the previous state.
				elif TokenType.CLOSE_BRACE == self.parser._curToken[0]:
					if (!self._parseCloseBrace()):
						returnFromCall = True

				# We're executing a control word. Execute this before
				# appending tokens to any special destination or group that
				# might contain control words.
				elif TokenType.CONTROL_WORDORSYM == self.parser._curToken[0]:
					tokenParts = self.__splitControlWord(self.parser._curToken)
					if (!self._parseControl(tokenParts[0], tokenParts[1])):
						returnFromCall = True

				# Just an ordinary printable character (note that literal
				# newlines are ignored. Only \line will result in an inserted \n.
				else:
					if (!self._parseCharacter(self.parser._curToken[1])):
						returnFromCall = True

				self.parser._prevToken = self.parser._curToken
				self.parser._curToken = self._getNextToken()

