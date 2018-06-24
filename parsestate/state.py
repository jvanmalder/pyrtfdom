# -*- coding: utf-8 -*-

import re, time
from abc import ABCMeta, abstractmethod

from ..tokentype import TokenType

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

		if not self._parser._content[self._parser._curPos].isalpha() and not self._parser._content[self._parser._curPos].isspace():

			# Character represented in \'xx form (if no hexadecimal digit
			# follows, it will be the responsibility of the parser to treat it
			# as an unsupported control symbol.)
			if "'" == self._parser._content[self._parser._curPos]:
				token = token + self._parser._content[self._parser._curPos]
				self._parser._curPos = self._parser._curPos + 1
				decimalCount = 0
				while decimalCount < 2 and (
					self._parser._content[self._parser._curPos].isdigit() or
					self._parser._content[self._parser._curPos].upper() in ['A', 'B', 'C', 'D', 'E']
				):
					token = token + self._parser._content[self._parser._curPos]
					self._parser._curPos = self._parser._curPos + 1
					decimalCount += 1

			# Control symbol
			else:
				token = token + self._parser._content[self._parser._curPos]
				self._parser._curPos = self._parser._curPos + 1

		# Control word
		elif self._parser._content[self._parser._curPos].isalpha():

			while self._parser._content[self._parser._curPos].isalpha():
				token = token + self._parser._content[self._parser._curPos]
				self._parser._curPos = self._parser._curPos + 1

			# Control word has a numeric parameter
			digitIndex = self._parser._curPos
			if self._parser._content[self._parser._curPos].isdigit() or '-' == self._parser._content[self._parser._curPos]:
				while self._parser._content[self._parser._curPos].isdigit() or (self._parser._curPos == digitIndex and '-' == self._parser._content[self._parser._curPos]):
					token = token + self._parser._content[self._parser._curPos]
					self._parser._curPos = self._parser._curPos + 1

			# If there's a single space that serves as a delimiter, the spec says
			# we should append it to the control word.
			if self._parser._content[self._parser._curPos].isspace():
				token = token + self._parser._content[self._parser._curPos]
				self._parser._curPos = self._parser._curPos + 1

		else:
			raise ValueError("Encountered unescaped '\\'")

		return token

	###########################################################################

	# Get next token from the currently loaded RTF
	def _getNextToken(self):

		# We haven't opened an RTF yet
		if not self._parser._content:
			return False

		# We've reached the end of the file
		elif self._parser._curPos >= len(self._parser._content):
			return [TokenType.EOF, '']

		# Control words and their parameters count as single tokens
		elif '\\' == self._parser._content[self._parser._curPos]:
			self._parser._curPos = self._parser._curPos + 1
			return [TokenType.CONTROL_WORDORSYM, self._getControlWordOrSymbol()]

		# Covers '{', '}' and any other character
		else:

			tokenType = TokenType.CHARACTER

			if '{' == self._parser._content[self._parser._curPos]:
				tokenType = TokenType.OPEN_BRACE
			elif '}' == self._parser._content[self._parser._curPos]:
				tokenType = TokenType.CLOSE_BRACE

			self._parser._curPos = self._parser._curPos + 1
			return [tokenType, self._parser._content[self._parser._curPos - 1]]

	###########################################################################

	# Defines what we should do when we encounter an open brace token. By
	# default, we just push the current state onto the stack and create a new
	# local copy. If a particular parsing state requires us to handle this
	# token differently, then its class should override this method. If we
	# return false instead of true, it means we should return from the current
	# call to self.parse().
	def _parseOpenBrace(self):

		self._parser._pushStateStack()
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

		oldStateCopy = self._parser.curState
		oldStateFull = self._parser.fullState # used in call to onStateChange
		self._parser._popStateStack()

		if callOnStateChange:
			callback = self._parser._getCallback('onStateChange')
			if callback:
				callback(self._parser, oldStateFull, self._parser.fullState)

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

		if '\\\\' == word:
			self._parser._appendToCurrentParagraph('\\')

		elif '\\{' == word:
			self._parser._appendToCurrentParagraph('{')

		elif '\\}' == word:
			self._parser._appendToCurrentParagraph('}')

		################################################
		#     Unicode and other special Characters     #
		################################################

		# Non-breaking space
		elif '\\~' == word:
			self._parser._appendToCurrentParagraph('\N{NO-BREAK SPACE}')

		# Non-breaking hyphen
		elif '\\_' == word:
			self._parser._appendToCurrentParagraph('\N{NON-BREAKING HYPHEN}')

		# A space character with the width of the letter 'm' in the current font
		elif '\\emspace' == word:
			self._parser._appendToCurrentParagraph('\N{EM SPACE}')

		# A space character with the width of the letter 'n' in the current font
		elif '\\enspace' == word:
			self._parser._appendToCurrentParagraph('\N{EN SPACE}')

		# En dash
		elif '\\endash' == word:
			self._parser._appendToCurrentParagraph('\N{EN DASH}')

		# Em dash
		elif '\\emdash' == word:
			self._parser._appendToCurrentParagraph('\N{EM DASH}')

		# Left single quote
		elif '\\lquote' == word:
			self._parser._appendToCurrentParagraph('\N{LEFT SINGLE QUOTATION MARK}')

		# Right single quote
		elif '\\rquote' == word:
			self._parser._appendToCurrentParagraph('\N{RIGHT SINGLE QUOTATION MARK}')

		# Left double quote
		elif '\\ldblquote' == word:
			self._parser._appendToCurrentParagraph('\N{LEFT DOUBLE QUOTATION MARK}')

		# Right double quote
		elif '\\rdblquote' == word:
			self._parser._appendToCurrentParagraph('\N{RIGHT DOUBLE QUOTATION MARK}')

		# Non-paragraph-breaking line break
		elif '\\line' == word:
			self._parser._appendToCurrentParagraph('\n')

		# Tab character
		elif '\\tab' == word:
			self._parser._appendToCurrentParagraph('\t')

		# tab
		elif '\\bullet' == word:
			self._parser._appendToCurrentParagraph('\N{BULLET}')

		# Current date (long form)
		elif '\\chdate' == word or '\\chdpl' == word:
			self._parser._appendToCurrentParagraph(time.strftime("%A, %B %d, %Y"))

		# Current date (abbreviated form)
		elif '\\chdpa' == word:
			self._parser._appendToCurrentParagraph(time.strftime("%m/%d/%Y"))

		# Current date (abbreviated form)
		elif '\\chtime' == word:
			self._parser._appendToCurrentParagraph(time.strftime("%I:%M:%S %p"))

		# A character of the form \uXXX to be added to the current paragraph.
		# Unlike \'XX, \u takes a decimal number instead of hex.
		elif '\\u' == word and param:
			try:
				self._parser._appendToCurrentParagraph(chr(int(param, 10)))
			except ValueError:
				return

		# A character of the form \'XX to be added to the current paragraph
		elif "\\'" == word and param:

			try:

				charCode = int(param, 16)
				prevTokenParts = self.__splitControlWord(self._parser._prevToken)

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
					self._parser._appendToCurrentParagraph(chr(charCode))

			except ValueError:
				return

		################################################
		#        Misc control words and symbols        #
		################################################

		# We're inserting a page break into the current paragraph
		elif '\\page' == word or '\\pagebb' == word:
			self._parser._breakPage()

		# We're ending the current paragraph and starting a new one
		elif '\\par' == word:
			self._parser._closeParagraph()
			self._parser._openParagraph()

		# Reset all styling to an off position in the current state
		elif '\\plain' == word:
			self._parser._resetStateFormattingAttributes()

		# Paragraph alignment
		elif '\\ql' == word:
			self._parser._setStateValue('alignment', 'left')

		elif '\\qr' == word:
			self._parser._setStateValue('alignment', 'right')

		elif '\\qc' == word:
			self._parser._setStateValue('alignment', 'center')

		elif '\\qd' == word:
			self._parser._setStateValue('alignment', 'distributed')

		elif '\\qj' == word:
			self._parser._setStateValue('alignment', 'justified')

		elif '\\qt' == word:
			self._parser._setStateValue('alignment', 'thai-distributed')

		# TODO: how do I want to handle \qkN alignment? Will require setting
		# two attributes.

		# Italic
		elif '\\i' == word:
			if param is None or '1' == param:
				self._parser._setStateValue('italic', True)
			else:
				self._parser._setStateValue('italic', False)

		# Bold
		elif '\\b' == word:
			if param is None or '1' == param:
				self._parser._setStateValue('bold', True)
			else:
				self._parser._setStateValue('bold', False)

		# Underline
		elif '\\ul' == word:
			if param is None or '1' == param:
				self._parser._setStateValue('underline', True)
			else:
				self._parser._setStateValue('underline', False)

		# Strike-through
		elif '\\strike' == word:
			if param is None or '1' == param:
				self._parser._setStateValue('strikethrough', True)
			else:
				self._parser._setStateValue('strikethrough', False)

		return True

	###########################################################################

	# Defines what we should do when we encounter an ordinary character token.
	# If function returns false instead of true, it means we should return from
	# the current call to self.parse().
	@abstractmethod
	def _parseCharacter(self, token):
		pass

	###########################################################################

	# Parse the RTF and return an array of formatted paragraphs. TODO: You'll
	# note that when parsing heavy data (like large embedded images), the
	# performance of this refactor is significantly worse than the way I'd
	# implemented it originally due to the high cost of Python's function call
	# overhead. I'm not sure what to do about this yet...
	def parse(self):

		if self._parser._content:

			self._parser._curToken = self._getNextToken()

			while TokenType.EOF != self._parser._curToken[0]:

				if TokenType.OPEN_BRACE == self._parser._curToken[0]:
					if not self._parseOpenBrace():
						return

				# Restore the previous state.
				elif TokenType.CLOSE_BRACE == self._parser._curToken[0]:
					if not self._parseCloseBrace():
						return

				# We're executing a control word. Execute this before
				# appending tokens to any special destination or group that
				# might contain control words.
				elif TokenType.CONTROL_WORDORSYM == self._parser._curToken[0]:
					tokenParts = self.__splitControlWord(self._parser._curToken)
					if not self._parseControl(tokenParts[0], tokenParts[1]):
						return

				# Just an ordinary printable character (note that literal
				# newlines are ignored. Only \line will result in an inserted \n.
				elif not self._parseCharacter(self._parser._curToken[1]):
						return

				self._parser._prevToken = self._parser._curToken
				self._parser._curToken = self._getNextToken()

