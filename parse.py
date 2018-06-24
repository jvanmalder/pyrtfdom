# -*- coding: utf-8 -*-

# A simple RTF parser based loosely on the 1.9.1 standard. This is intended
# primarily to extract formatted text, but could easily be extended and turned
# into a general parser in the future.

import binascii, copy

from .parsestate.main import MainState
from .tokentype import TokenType

###############################################################################

class RTFParser(object):

	# Text formatting attributes and their default values. Values with booleans
	# should be set to either True (for on) or False (for off.) If an attribute
	# doesn't exist in the current state, it means we must retrieve its value
	# from the first state up the stack where it's defined.
	__stateFormattingAttributes = {
		'italic':        False,
		'bold':          False,
		'underline':     False,
		'strikethrough': False,
		'alignment':     'left'
	}

	__specialStateVars = [
		'groupSkip',      # we're skipping the current group
		'inField',        # we're inside a {\field} group
		'inFieldinst',    # we're inside the {\fldinst} portion of a \field
		'inFieldrslt',    # we're inside the {\fldrslt} portion of a \field
		'inPict',         # We're currently parsing an embedded image
		'pictAttributes', # Attributes assigned to the image we're currently parsing
		'inBlipUID',      # We're parsing an image's unique ID
		'blipUID'         # Contains an image's unique ID
	]

	###########################################################################

	# Read-only public access to the full state.
	@property
	def fullState(self):

		# TODO: benchmark with and without copy, and if it's significantly
		# faster without it, get rid of this. Can try self.__fullStateCache.copy()...
		return copy.deepcopy(self.__fullStateCache)

	###########################################################################

	# Read-only public access to the current partial state.
	@property
	def curState(self):

		return copy.deepcopy(self.__curState)

	###########################################################################

	# Content
	def __init__(self, options):

		self.reset()

		# This class only parses the RTF. How that data is encoded and represented
		# after parsing is up to the client, and the client should provide a
		# at least a minimum number of callbacks to process that data as it's
		# extracted from the RTF.
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

	# Crawls up the state stack to fill in any attributes in the current state
	# that are inherited from a previous state, then caches the result in
	# self.__fullStateCache.
	def __cacheFullState(self):

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

		self.__fullStateCache = state
		return state

	###########################################################################

	# Pushes the current state onto the state stack and sets up a new clean
	# state.
	def _pushStateStack(self):

		self.__stateStack.append(self.__curState)
		self.__curState = {}

	###########################################################################

	# Pops the last state from the stack and restores self.__curState.
	def _popStateStack(self):

		self.__curState = self.__stateStack.pop()
		self.__cacheFullState() # Update the full state cache
		return self.__curState

	###########################################################################

	# Inserts a page break into the current paragraph.
	def _breakPage(self):

		if 'onPageBreak' in self.__options['callbacks']:
			self.__options['callbacks']['onPageBreak'](self)

	###########################################################################

	# Opens a new paragraph.
	def _openParagraph(self):

		self.__options['callbacks']['onOpenParagraph'](self)

	###########################################################################

	# Appends the specified string to the current paragraph.
	def _appendToCurrentParagraph(self, string):

		self.__options['callbacks']['onAppendParagraph'](self, string)

	###########################################################################

	# Closes the current paragraph.
	def _closeParagraph(self):

		if 'onCloseParagraph' in self.__options['callbacks']:
			self.__options['callbacks']['onCloseParagraph'](self)

	###########################################################################

	# Reset the current state's formatting attributes to their default values.
	def _resetStateFormattingAttributes(self, doCallback = True):

		formerState = self.__fullStateCache

		for attribute in self.__stateFormattingAttributes.keys():
			self.__curState[attribute] = self.__stateFormattingAttributes[attribute]

		# Update the full state cache now that the attributes have changed
		self.__cacheFullState()

		if doCallback and 'onStateChange' in self.__options['callbacks']:
			self.__options['callbacks']['onStateChange'](self, formerState, self.__fullStateCache)

	###########################################################################

	# Sets a state value. Styling attributes (bold, italic, etc.) should trigger
	# the onStateChange event. Boolean styling values like italic, bold, etc.
	# should be set to True or False. Not doing so will result in undefined
	# behavior. State values that are used internally and that don't effect the
	# output can be set to whatever you want and should not trigger onStateChange.
	def _setStateValue(self, attribute, value, triggerOnStateChange = True):

		oldState = self.__fullStateCache
		self.__curState[attribute] = value

		# Update the full state cache now that the attribute has changed
		self.__cacheFullState()

		if triggerOnStateChange and 'onStateChange' in self.__options['callbacks']:
			self.__options['callbacks']['onStateChange'](self, oldState, self.__fullStateCache)

	###########################################################################

	# Sets a document level attribute (not the same as a formatting attribute.)
	# Examples are the value of \*\generator, etc. This means nothing to the
	# parser itself, and will do nothing unless a callback has been registered
	# to handle it.
	def _setDocumentAttribute(self, attribute, value):

		if 'onSetDocumentAttribute' in self.__options['callbacks']:
			self.__options['callbacks']['onSetDocumentAttribute'](self, attribute, value)

	###########################################################################

	# Reset to a default state where all the formatting attributes are turned off.
	def _initState(self):

		self.__curState = {}
		self._resetStateFormattingAttributes(False)
		self.__curState['groupSkip'] = False
		self.__curState['inField'] = False

		self.__fullStateCache = self.__curState.copy()

	###########################################################################

	# Resets the parser to an initialized state so we can parse another document.
	def reset(self):

		# A string containing the content of an RTF file
		self._content = False

		# Our current index into self._content
		self._curPos = 0

		# Formatting states at various levels of curly braces
		self.__stateStack = []

		# Values that were set in the current formatting state. To see the full
		# state, view the contents of self.__fullStateCache (make sure to call 
		# self.__cacheFullState() whenever the state changes.)
		self.__curState = False

		# Walking through the state stack to construct a full representation of
		# the current state is expensive. Therefore, we should only do so once
		# whenever the state actually changes, then cache the result as long as
		# the state stays the same so we can refer back to it frequently without
		# slowing things down. I discovered the need for this after profiling.
		self.__fullStateCache = False

		# Stores the current token during parsing
		self._curToken = False

		# Records the previously retrieved token during parsing
		self._prevToken = False

	###########################################################################

	# Returns true if the specified attribute is a formatting attribute and false
	# if not.
	def isAttributeFormat(self, attr):

		if attr in self.__stateFormattingAttributes:
			return True
		else:
			return False

	###########################################################################

	# Parse an RTF file.
	def openFile(self, filename):

		self.reset()
		rtfFile = open(filename, 'r')
		self._content = rtfFile.read()
		rtfFile.close()

	###########################################################################

	# Parse an RTF from an already loaded string.
	def openString(self, rtfContent):

		self.reset()
		self._content = rtfContent

	###########################################################################

	# Enter the default parser state and begin parsing the document.
	def parse(self):

		mainState = MainState(self)
		mainState.parse()

