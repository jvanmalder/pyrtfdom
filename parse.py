# -*- coding: utf-8 -*-

# A simple RTF parser based loosely on the 1.9.1 standard. This is intended
# primarily to extract formatted text, but could easily be extended and turned
# into a general parser in the future.

import copy

from .parsestate.main import MainState
from .tokentype import TokenType

###############################################################################

class RTFParser(object):

	# Formatting attributes and their default values. Values with booleans
	# should be set to either True (for on) or False (for off.) If an attribute
	# doesn't exist in the current state, it means we must retrieve its value
	# from the first state up the stack where it's defined.
	__formattingAttributes = {

		# TODO
		'document': {},
		'section':  {},
		'table':    {},

		# Paragraph formatting properties
		'paragraph': {
			'style':     'Normal',
			'alignment': 'left',
			'pagebreakBefore': False
		},

		# Character formatting properties
		# An fColor or bColor of False indicates \c0, the "auto" color. If a
		# different color is defined, this will be set to a dict with the
		# following properties: 'red', 'green', 'blue', 'shade' and 'tint'.
		'character': {
			'italic':        False,
			'bold':          False,
			'underline':     False,
			'strikethrough': False,
			'fColor':        False,
			'bColor':        False
		}
	}

	###########################################################################

	# Read-only "protected" access to the full state. This is really only
	# necessary when we're going to be passing objects stored in the state
	# outside of our trusted parsing classes. An example would be when the
	# onStateChange event is triggered.
	@property
	def _fullState(self):

		return copy.deepcopy(self._fullStateCache)

	###########################################################################

	# Read-only public access to the full state's public attributes. Deep copy
	# is slow, so if you need to hit this a lot, be a little bad and access
	# self._fullStateCache directly. Just promise not to change anything O:-)
	@property
	def fullStateAttributes(self):

		return {
			'document':  copy.deepcopy(self._fullStateCache['document']),
			'section':   copy.deepcopy(self._fullStateCache['section']),
			'table':     copy.deepcopy(self._fullStateCache['table']),
			'paragraph': copy.deepcopy(self._fullStateCache['paragraph']),
			'character': copy.deepcopy(self._fullStateCache['character'])
		}

	###########################################################################

	# Creates a new state.
	def __createState(self):

		return {
			'document':  {},
			'section':   {},
			'table':     {},
			'paragraph': {},
			'character': {},
			'private':   {}
		}

	###########################################################################

	# Content
	def __init__(self, options):

		self.reset()

		# This class only parses the RTF. How that data is encoded and
		# represented after parsing is up to the client, and the client should
		# provide at least a minimum number of callbacks to process that data as
		# it's extracted from the RTF.
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
	# self._fullStateCache.
	def __cacheFullState(self):

		state = self._curState.copy()

		if len(self.__stateStack):
			for i in reversed(range(len(self.__stateStack))):
				for namespace in self.__stateStack[i].keys():
					if (namespace not in state):
						state[namespace] = {}
					for attribute in self.__stateStack[i][namespace].keys():
						if attribute not in state[namespace]:
							state[namespace][attribute] = self.__stateStack[i][namespace][attribute]

		self._fullStateCache = state
		return state

	###########################################################################

	# Updates the default formatting attributes. Useful when, for example, we're
	# parsing \s0 (default paragraph style) in an RTF stylesheet. See comment
	# inside function for explanation of uglyStateFix parameter.
	def _updateDefaultAttributes(self, attributeType, attributes, uglyStateFix = False):

		for attribute in attributes['attributes'].keys():
			self.__formattingAttributes[attributeType][attribute] = attributes['attributes'][attribute]

		# UGLY HACK ALERT: by the time the stylesheet attribute has been parsed,
		# we've already pushed an initial state on the stack which contains the
		# old pre-stylesheet defaults. I have to make sure this state is updated
		# according to the new defaults. Set uglyStateFix to true only when
		# we're calling this immediately after parsing the stylesheet.
		if uglyStateFix and len(self.__stateStack):
			for attribute in attributes['attributes'].keys():
				self.__stateStack[0][attributeType][attribute] = attributes['attributes'][attribute]
			self.__cacheFullState()

	###########################################################################

	# Returns the specified callback function if it exists, or None if it
	# doesn't.
	def _getCallback(self, callbackName):

		if callbackName in self.__options['callbacks']:
			return self.__options['callbacks'][callbackName]
		else:
			return None

	###########################################################################

	# Pushes the current state onto the state stack and sets up a new clean
	# state.
	def _pushStateStack(self):

		self.__stateStack.append(self._curState)
		self._curState = self.__createState()

	###########################################################################

	# Pops the last state from the stack and restores self._curState.
	def _popStateStack(self):

		self._curState = self.__stateStack.pop()
		self.__cacheFullState() # Update the full state cache
		return self._curState

	###########################################################################

	# Inserts a page break into the current paragraph.
	def _breakPage(self):

		callback = self._getCallback('onPageBreak')
		if callback:
			callback(self)

	###########################################################################

	# Opens a new paragraph.
	def _openParagraph(self):

		callback = self._getCallback('onOpenParagraph')
		if callback:
			callback(self)

	###########################################################################

	# Appends the specified string to the current paragraph.
	def _appendToCurrentParagraph(self, string):

		callback = self._getCallback('onAppendParagraph')
		if callback:
			callback(self, string)

	###########################################################################

	# Closes the current paragraph.
	def _closeParagraph(self):

		callback = self._getCallback('onCloseParagraph')
		if callback:
			callback(self)

	###########################################################################

	# Reset the current state's formatting attributes to their default values.
	def _resetStateFormattingAttributes(self, doCallback = True):

		formerStateAttributes = self._fullState
		formerStateAttributes.pop('private', None) # Only return publicly accessible attributes

		for attributeType in self.__formattingAttributes.keys():
			for attribute in self.__formattingAttributes[attributeType].keys():
				self._curState[attributeType][attribute] = self.__formattingAttributes[attributeType][attribute]

		# Update the full state cache now that the attributes have changed
		self.__cacheFullState()

		# Pass in both the previous and current state attributes
		newStateAttributes = self._fullState
		newStateAttributes.pop('private', None)

		if doCallback:
			callback = self._getCallback('onStateChange')
			if callback:
				callback(self, formerStateAttributes, newStateAttributes)

	###########################################################################

	# Sets either a public attribute or a private state value. Values set in a
	# publicly accessible namespace trigger the onStateChange event. Boolean
	# attribute values like italic, bold, etc. should be set to True or False.
	# Not doing so will result in wonky behavior.
	def _setStateValue(self, namespace, attribute, value):

		oldStateAttributes = self._fullState
		oldStateAttributes.pop('private', None)

		self._curState[namespace][attribute] = value

		# Update the full state cache now that the attribute has changed
		self.__cacheFullState()

		newStateAttributes = self._fullState
		newStateAttributes.pop('private', None)

		# If we're not setting a private state variable, call the onStateChange
		# callback
		if namespace in self.__formattingAttributes.keys():
			callback = self._getCallback('onStateChange')
			if callback:
				callback(self, oldStateAttributes, newStateAttributes)

	###########################################################################

	# Reset to a default state where all the formatting attributes are turned off.
	def _initState(self):

		self._curState = self.__createState()
		self._fullStateCache = self._curState.copy()
		self._resetStateFormattingAttributes(False)

	###########################################################################

	# Adds a new style to the stylesheet. styleType should be one of 'section',
	# 'table', 'paragraph' or 'character'. styleIndex is how the style is named
	# in the RTF. For example, \s1 would have styleType = 'paragraph' and
	# styleIndex = 1. Properties should be a dict object defined as follows:
	# {name: '<style name as defined in RTF stylesheet>', attributes: <dict with
	# attributes that should be turned on in the current state whenever the style
	# is encountered later during parsing>}.
	def _insertStyle(self, styleType, styleIndex, properties):

		self.__stylesheet[styleType][int(styleIndex)] = properties

	###########################################################################

	# Return the style of the specified type and index if it exists in the
	# stylesheet and None if not.
	def _getStyle(self, styleType, styleIndex):

		if styleType in self.__stylesheet and int(styleIndex) in self.__stylesheet[styleType]:
			return self.__stylesheet[styleType][int(styleIndex)]
		else:
			return None

	###########################################################################

	# Insert a color into the color table.
	def _insertColor(self, color):

		self.__colortable.push(color)

	###########################################################################

	# Returns the color from the color table at the specified index if it exists
	# and None if it doesn't.
	def _getColor(self, index):

		if int(index) < len(self.__colortable):
			return self.__colortable[int(index)]
		else:
			return None

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
		# state, view the contents of self._fullStateCache (make sure to call 
		# self.__cacheFullState() whenever the state changes.)
		self._curState = False

		# Walking through the state stack to construct a full representation of
		# the current state is expensive. Therefore, we should only do so once
		# whenever the state actually changes, then cache the result as long as
		# the state stays the same so we can refer back to it frequently without
		# slowing things down. I discovered the need for this after profiling.
		self._fullStateCache = False

		# Stores the current token during parsing
		self._curToken = False

		# Records the previously retrieved token during parsing
		self._prevToken = False

		# Styles parsed out of the RTF's stylesheet
		self.__stylesheet = {
			'section':   {},
			'table':     {},
			'paragraph': {},
			'character': {}
		}

		# Defined in \colortbl
		self.__colortable = [
			False # \s0 will always be the default "auto" color
		]

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

		# Initialize markers representing our current place in the document
		self._curToken = False
		self._prevToken = False

		# Start with a default state where all the formatting attributes are
		# turned off.
		self._initState()

		# Open our initial paragraph
		self._openParagraph()

		# Begin parsing
		mainState = MainState(self)
		mainState.parse()

	###########################################################################

	# Debugging method to print out the contents of the stylesheet.
	def printStylesheet(self):

		print('RTF Stylesheet:')
		print(self.__stylesheet)

	###########################################################################

	# Debugging method to print out the contents of the color table.
	def printColorTable(self):

		print('RTF Color Table:')
		print(self.__colortable)

