# -*- coding: utf-8 -*-

# A simple RTF parser based loosely on the 1.9.1 standard. This is intended
# primarily to extract formatted text, but could easily be extended and turned
# into a general parser in the future.

import re, time
from enum import Enum

class RTFParser(object):

	# Token types
	class TokenType(Enum):
		OPEN_BRACE        = 1
		CLOSE_BRACE       = 2
		CONTROL_WORDORSYM = 3
		CHARACTER         = 4
		EOF               = 5

	# Text formatting attributes and their default values. Values with booleans
	# should be set to either True (for on) or False (for off.) If an attribute
	# doesn't exist in the current state, it means we must retrieve its value
	# from the first state up the stack where it's defined.
	__stateFormattingAttributes = {
		'italic':        False,
		'bold':          False,
		'underline':     False,
		'strikethrough': False
	}

	__specialStateVars = [
		'groupSkip',   # we're skipping the current group
		'inField',     # we're inside a {\field} group
		'inFieldinst', # we're inside the {\fldinst} portion of a \field
		'inFieldrslt'  # we're inside the {\fldrslt} portion of a \field
	]

	###########################################################################

	# Content
	def __init__(self, options):

		# A string containing the content of an RTF file
		self.__content = False

		# Our current index into self.__content
		self.__curPos = 0

		# Formatting states at various levels of curly braces
		self.__stateStack = []

		# The current formatting state
		self.__curState = False

		# Stores the current token during parsing
		self.__curToken = False

		# Records the previously retrieved token during parsing
		self.__prevToken = False

		# This class only parses the RTF. How that data is encoded and represented
		# after parsing is up to the client, and the client should provide a
		# at least a minimum number of callbacks to process that data after it's
		# extracted from the RTF file.
		if not options or 'callbacks' not in options:
			raise Exception('Did not pass required callbacks.')
		elif (
			'onOpenParagraph'   not in options['callbacks'] or
			'onAppendParagraph' not in options['callbacks'] or
			'onStateChange'     not in options['callbacks'] or
			'onField'           not in options['callbacks']
		):
			raise Exception('Did not pass required callbacks.')

		self.__options = options

	###########################################################################

	# Get the control word or symbol at the current position
	def __getControlWordOrSymbol(self):

		token = '\\'

		if not self.__content[self.__curPos].isalpha() and not self.__content[self.__curPos].isspace():

			# Character represented in \'xx form (if no digit follows, it will
			# be the responsibility of the parser to treat it as an unsupported
			# control symbol.)
			if "'" == self.__content[self.__curPos]:
				token = token + self.__content[self.__curPos]
				self.__curPos = self.__curPos + 1
				while self.__content[self.__curPos].isdigit():
					token = token + self.__content[self.__curPos]
					self.__curPos = self.__curPos + 1

			# Control symbol
			else:
				token = token + self.__content[self.__curPos]
				self.__curPos = self.__curPos + 1

		# Control word
		elif self.__content[self.__curPos].isalpha():

			while self.__content[self.__curPos].isalpha():
				token = token + self.__content[self.__curPos]
				self.__curPos = self.__curPos + 1

			# Control word has a numeric parameter
			digitIndex = self.__curPos
			if self.__content[self.__curPos].isdigit() or '-' == self.__content[self.__curPos]:
				while self.__content[self.__curPos].isdigit() or (self.__curPos == digitIndex and '-' == self.__content[self.__curPos]):
					token = token + self.__content[self.__curPos]
					self.__curPos = self.__curPos + 1

			# If there's a single space that serves as a delimiter, the spec says
			# we should append it to the control word.
			if self.__content[self.__curPos].isspace():
				token = token + self.__content[self.__curPos]
				self.__curPos = self.__curPos + 1

		else:
			raise ValueError("Encountered unescaped '\\'")

		return token

	###########################################################################

	# Get next token from the currently loaded RTF
	def __getNextToken(self):

		# We haven't opened an RTF yet
		if not self.__content:
			return False

		# We've reached the end of the file
		elif self.__curPos >= len(self.__content):
			return [self.TokenType.EOF, '']

		# Control words and their parameters count as single tokens
		elif '\\' == self.__content[self.__curPos]:
			self.__curPos = self.__curPos + 1
			return [self.TokenType.CONTROL_WORDORSYM, self.__getControlWordOrSymbol()]

		# Covers '{', '}' and any other character
		else:

			tokenType = self.TokenType.CHARACTER

			if '{' == self.__content[self.__curPos]:
				tokenType = self.TokenType.OPEN_BRACE
			elif '}' == self.__content[self.__curPos]:
				tokenType = self.TokenType.CLOSE_BRACE

			self.__curPos = self.__curPos + 1
			return [tokenType, self.__content[self.__curPos - 1]]

	###########################################################################

	# Opens a new paragraph.
	def __openParagraph(self):

		self.__options['callbacks']['onOpenParagraph'](self)

	###########################################################################

	# Appends the specified string to the current paragraph.
	def __appendToCurrentParagraph(self, string):

		self.__options['callbacks']['onAppendParagraph'](self, string)

	###########################################################################

	# Closes the current paragraph.
	def __closeParagraph(self):

		if 'onCloseParagraph' in self.__options['callbacks']:
			self.__options['callbacks']['onCloseParagraph'](self)

	###########################################################################

	# Reset the current state's formatting attributes to their default values.
	def __resetStateFormattingAttributes(self, doCallback = True):

		formerState = self.getFullState()

		for attribute in self.__stateFormattingAttributes.keys():
			self.__curState[attribute] = self.__stateFormattingAttributes[attribute]

		if doCallback and 'onStateChange' in self.__options['callbacks']:
			self.__options['callbacks']['onStateChange'](self, formerState, self.getFullState())

	###########################################################################

	# Sets a styling attribute (bold, italic, etc.) Boolean values like italic,
	# bold, etc. should be set to True or False. Not doing so will result in
	# undefined behavior.
	def __setStateFormattingAttribute(self, attribute, value):

		oldState = self.getFullState()
		self.__curState[attribute] = value

		if 'onStateChange' in self.__options['callbacks']:
			self.__options['callbacks']['onStateChange'](self, oldState, self.getFullState())

	###########################################################################

	# Process a \field group.
	def __parseField(self, fldinst, fldrslt):

		# We let the callback handle it
		if 'onField' in self.__options['callbacks']:
			self.__options['callbacks']['onField'](self, fldinst, fldrslt)

		# There's no callback that knows how to handle it, so we'll just do things
		# the dumb way by appending the \fldrslt value to the current paragraph.
		else:
			self.__appendToCurrentParagraph(fldrslt)

	###########################################################################

	# Executes a control word or symbol
	def __executeControl(self, word, param):

		# If we're parsing a \fldinst value and encounter another control word
		# with the \* prefix, we know we're done parsing the parts of \fldinst
		# we care about (this will change as I handle more of the RTF spec.)
		if '\\*' == word and 'inFieldinst' in self.__curState and self.__curState['inFieldinst']:
			self.__curState['inFieldinst'] = False

		################################################
		#       Part 1. Destinations and fields        #
		################################################

		# Skip over these sections. We're not going to use them (at least
		# for now.)
		if self.TokenType.OPEN_BRACE == self.__prevToken[0] and (
			word == '\\fonttbl' or
			word == '\\filetbl' or
			word == '\\colortbl' or
			word == '\\stylesheet'or
			word == '\\stylerestrictions' or
			word == '\\listtables' or
			word == '\\revtbl' or
			word == '\\rsidtable' or
			word == '\\mathprops' or
			word == '\\generator'
		):
			self.__curState['groupSkip'] = True

		# Beginning of a field
		elif self.TokenType.OPEN_BRACE == self.__prevToken[0] and '\\field' == word:
			self.__curState['inField'] = True

		# Most recent calculated result of field. In practice, this is also
		# the text that would be parsed into the paragraph by an RTF reader
		# that doesn't understand fields.
		elif self.TokenType.OPEN_BRACE == self.__prevToken[0] and '\\fldrslt' == word:
			self.__curState['inFieldrslt'] = True

		# Field instruction
		elif '\\*' == self.__prevToken[1] and '\\fldinst' == word:
				self.__curState['inFieldinst'] = True

		################################################
		#      Part 2. Escaped special characters      #
		################################################

		elif '\\\\' == word:
			self.__appendToCurrentParagraph('\\')

		elif '\\{' == word:
			self.__appendToCurrentParagraph('{')

		elif '\\}' == word:
			self.__appendToCurrentParagraph('}')

		################################################
		# Part 3. Unicode and other special Characters #
		################################################

		# Non-breaking space
		elif '\\~' == word:
			self.__appendToCurrentParagraph('\N{NO-BREAK SPACE}')

		# Non-breaking hyphen
		elif '\\_' == word:
			self.__appendToCurrentParagraph('\N{NON-BREAKING HYPHEN}')

		# A space character with the width of the letter 'm' in the current font
		elif '\\emspace' == word:
			self.__appendToCurrentParagraph('\N{EM SPACE}')

		# A space character with the width of the letter 'n' in the current font
		elif '\\enspace' == word:
			self.__appendToCurrentParagraph('\N{EN SPACE}')

		# En dash
		elif '\\endash' == word:
			self.__appendToCurrentParagraph('\N{EN DASH}')

		# Em dash
		elif '\\emdash' == word:
			self.__appendToCurrentParagraph('\N{EM DASH}')

		# Left single quote
		elif '\\lquote' == word:
			self.__appendToCurrentParagraph('\N{LEFT SINGLE QUOTATION MARK}')

		# Right single quote
		elif '\\rquote' == word:
			self.__appendToCurrentParagraph('\N{RIGHT SINGLE QUOTATION MARK}')

		# Left double quote
		elif '\\ldblquote' == word:
			self.__appendToCurrentParagraph('\N{LEFT DOUBLE QUOTATION MARK}')

		# Right double quote
		elif '\\rdblquote' == word:
			self.__appendToCurrentParagraph('\N{RIGHT DOUBLE QUOTATION MARK}')

		# Non-paragraph-breaking line break
		elif '\\line' == word:
			self.__appendToCurrentParagraph('\n')

		# Tab character
		elif '\\tab' == word:
			self.__appendToCurrentParagraph('\t')

		# tab
		elif '\\bullet' == word:
			self.__appendToCurrentParagraph('\N{BULLET}')

		# Current date (long form)
		elif '\\chdate' == word or '\\chdpl' == word:
			self.__appendToCurrentParagraph(time.strftime("%A, %B %d, %Y"))

		# Current date (abbreviated form)
		elif '\\chdpa' == word:
			self.__appendToCurrentParagraph(time.strftime("%m/%d/%Y"))

		# Current date (abbreviated form)
		elif '\\chtime' == word:
			self.__appendToCurrentParagraph(time.strftime("%I:%M:%S %p"))

		# A character of the form \uXXX to be added to the current paragraph.
		# Unlike \'XX, \u takes a decimal number instead of hex.
		elif '\\u' == word and param:
			try:
				self.__appendToCurrentParagraph(chr(int(param, 10)))
			except ValueError:
				return

		# A character of the form \'XX to be added to the current paragraph
		elif "\\'" == word and param:

			try:

				charCode = int(param, 16)
				prevTokenParts = self.__splitControlWord(self.__prevToken)

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
					self.__appendToCurrentParagraph(chr(charCode))

			except ValueError:
				return

		################################################
		#  Part 4. Ordinary control words and symbols  #
		################################################

		# We're ending the current paragraph and starting a new one
		elif '\\par' == word:
			self.__closeParagraph()
			self.__openParagraph()

		# Reset all styling to an off position in the current state
		elif '\\plain' == word:
			self.__resetStateFormattingAttributes()

		# Italic
		elif '\\i' == word:
			if param is None or '1' == param:
				self.__setStateFormattingAttribute('italic', True)
			else:
				self.__setStateFormattingAttribute('italic', False)

		# Bold
		elif '\\b' == word:
			if param is None or '1' == param:
				self.__setStateFormattingAttribute('bold', True)
			else:
				self.__setStateFormattingAttribute('bold', False)

		# Underline
		elif '\\ul' == word:
			if param is None or '1' == param:
				self.__setStateFormattingAttribute('underline', True)
			else:
				self.__setStateFormattingAttribute('underline', False)

		# Strike-through
		elif '\\strike' == word:
			if param is None or '1' == param:
				self.__setStateFormattingAttribute('strikethrough', True)
			else:
				self.__setStateFormattingAttribute('strikethrough', False)

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

	# Returns true if the specified attribute is a formatting attribute and false
	# if not.
	def isAttributeFormat(self, attr):

		if attr in self.__stateFormattingAttributes:
			return True
		else:
			return False

	###########################################################################

	# Crawls up the state stack to fill in any attributes in the current state
	# that are inherited from a previous state.
	def getFullState(self):

		state = self.__curState.copy()

		for attribute in self.__stateFormattingAttributes.keys():
			if attribute not in state:
				for i in reversed(range(len(self.__stateStack))):
					if attribute in self.__stateStack[i]:
						state[attribute] = self.__stateStack[i][attribute]
						break

		# Special non-attribute state variables
		for stateVar in self.__specialStateVars:
			if stateVar not in state:
				for i in reversed(range(len(self.__stateStack))):
					if stateVar in self.__stateStack[i]:
						state[stateVar] = self.__stateStack[i][stateVar]
						break

		return state

	###########################################################################

	# Parse an RTF file.
	def openFile(self, filename):

		rtfFile = open(filename, 'r')
		self.__content = rtfFile.read()
		self.__curPos = 0
		rtfFile.close()

	###########################################################################

	# Parse an RTF from an already loaded string.
	def openString(self, rtfContent):

		self.__content = rtfContent
		self.__curPos = 0

	###########################################################################

	# Parse the RTF and return an array of formatted paragraphs.
	def parse(self):

		if self.__content:

			# Used as a temporary buffer for data inside a \field group
			fldInst = ''
			fldRslt = ''

			self.__curToken = self.__getNextToken()
			self.__prevToken = False

			# Start out with a default state where all the formatting attributes are
			# turned off.
			self.__curState = {}
			self.__resetStateFormattingAttributes(False)
			self.__curState['groupSkip'] = False
			self.__curState['inField'] = False

			# Open our initial paragraph
			self.__openParagraph()

			while self.TokenType.EOF != self.__curToken[0]:

				# Push the current state onto the stack and create a new local copy.
				if self.TokenType.OPEN_BRACE == self.__curToken[0]:
					self.__stateStack.append(self.__curState)
					self.__curState = {}

				# Restore the previous state.
				elif self.TokenType.CLOSE_BRACE == self.__curToken[0]:

					oldStateCopy = self.__curState.copy()
					oldStateFull = self.getFullState() # used in call to onStateChange
					self.__curState = self.__stateStack.pop()

					# If we're not skipping over a group or processing a field, call
					# the onCloseGroup hook.
					if (
						'groupSkip' not in oldStateCopy or
						not oldStateCopy['groupSkip']
					) and (
						'inField' not in oldStateCopy or
						not oldStateCopy['inField']
					) and 'onStateChange' in self.__options['callbacks']:
						self.__options['callbacks']['onStateChange'](self, oldStateFull, self.getFullState())

					# We just exited a \field group. Process it and then reset the
					# \field data buffer.
					if 'inField' in oldStateCopy and oldStateCopy['inField']:
						self.__parseField(fldInst, fldRslt)
						fldInst = ''
						fldRslt = ''

				# We could be skipping over something we're not going to use, such
				# as \fonttbl, \stylesheet, etc.
				elif not self.getFullState()['groupSkip']:

					# We're inside the fldrslt portion of a field. Test for this
					# and fieldinst before processing control words, because if
					# there are control words in the field, we're just going to
					# copy everything verbatim into the string and let the client
					# worry about passing it back to another instance of the
					# parser for processing. Hacky? Maybe. But it works.
					if 'inFieldrslt' in self.getFullState() and self.getFullState()['inFieldrslt']:
						fldRslt += self.__curToken[1]

					# We're inside the \fldinst portion of a field.
					elif 'inFieldinst' in self.getFullState() and self.getFullState()['inFieldinst']:
						fldInst += self.__curToken[1]

					# We're executing a control word.
					elif self.TokenType.CONTROL_WORDORSYM == self.__curToken[0]:
						tokenParts = self.__splitControlWord(self.__curToken)
						self.__executeControl(tokenParts[0], tokenParts[1])

					# Just an ordinary printable character (note that literal
					# newlines are ignored. Only \line will result in an inserted \n.
					else:
						if not self.getFullState()['inField'] and '\n' != self.__curToken[1]:
							self.__appendToCurrentParagraph(self.__curToken[1])

				self.__prevToken = self.__curToken
				self.__curToken = self.__getNextToken()

