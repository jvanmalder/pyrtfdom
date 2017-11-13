# -*- coding: utf-8 -*-

import copy

from pyrtfdom import elements
from pyrtfdom.parse import RTFParser

class RTFDOM(object):

	# Will reference the RTF Parser with custom callbacks
	parser = None

	# The head and current position in the DOM, respectively
	__rootNode = None
	__curNode = None

	###########################################################################

	# Finds the attribute DOM element closest to the current node, then calculates
	# and returns its distance from the root RTF node. If an element for the
	# given attribute doesn't exist in the chain from current to root node, -1
	# will be returned.
	def __distanceFromRoot(self, attribute):

		distance = 0
		node = self.__curNode

		# First, locate the attribute's node
		while node.nodeType != attribute:
			node = node.parent

		# Next, calculate its distance from the root
		while node != self.__rootNode:
			distance = distance + 1
			node = node.parent

		return distance

	###########################################################################

	# Appends the contents of a fldrslt RTF paragraph into the current paragraph.
	def __insertFldrslt(self, rtfString):

		curParNode = self.__curNode.parent

		# If the previous text element was empty, it's unnecessary and can be
		# removed to simplify the tree.
		if 0 == len(self.__curNode.value):
			curParNode.removeChild(self.__curNode)
			self.__curNode = curParNode

		subTree = RTFDOM()
		subTree.openString('{' + rtfString + '}')
		subTree.parse()

		subDOM = subTree.getTreeNodes()
		paraNode = subDOM.children[0]

		for child in paraNode.children:
			curParNode.appendChild(child)

		# Append a new text element after the contents of fldrslt so we can
		# continue appending text to the current paragraph.
		textNode = elements.TextElement()
		curParNode.appendChild(textNode)
		self.__curNode = textNode

	###########################################################################

	# Initializes the parser callbacks that are used to construct the DOM.
	def __initParserCallbacks(self):

		# Create a new paragraph and apply any styles that apply in the current
		# state.
		def onOpenParagraph(RTFParser):

			# Create the paragraph node
			para = elements.ParaElement()
			self.__rootNode.appendChild(para)
			self.__curNode = para

			# Any formatting attributes that are turned on in the current state
			# should be represented by their corresponding DOM elements
			state = RTFParser.getFullState()
			for attribute in state:
				if RTFParser.isAttributeFormat(attribute):
					if type(state[attribute]) == bool:
						if state[attribute]:
							node = elements.DOMElement.getElement(attribute)
							self.__curNode.appendChild(node)
							self.__curNode = node
					else:
						para.attributes[attribute] = state[attribute]

			# Create a text node where we'll append text for the paragraph
			textNode = elements.TextElement()
			self.__curNode.appendChild(textNode)
			self.__curNode = textNode

		#####

		# Append text to the current paragraph.
		def onAppendParagraph(RTFParser, text):

			self.__curNode.value += text

		#####

		# Whenever the state changes, we need to open/close DOM formatting
		# elements such as bold, italic, etc.
		def onStateChange(RTFParser, oldState, newState):

			# Keeps track of which attributes have been turned off and their DOM
			# element's distance from the root node.
			turnedOff = {}

			for attribute in newState:

				if attribute not in oldState.keys() or newState[attribute] != oldState[attribute]:

					# We're dealing with on/off attributes like bold, italic, etc.
					if type(newState[attribute]) == bool:

						# we're turning the attribute on
						if newState[attribute]:

							# elements[attribute] means the element type that
							# corresponds to the attribute
							node = elements.DOMElement.getElement(attribute)
							textNode = elements.TextElement()
							node.appendChild(textNode)
							self.__curNode.parent.appendChild(node)
							self.__curNode = textNode

						# we're turning the attribute off
						else:
							turnedOff[attribute] = self.__distanceFromRoot(attribute)

					# For now, any non-boolean attributes must be set at the
					# paragraph level (this could change as I implement more of
					# the RTF standard.)
					else:

						parNode = self.__curNode
						while 'para' != parNode.nodeType:
							parNode = parNode.parent

						parNode.attributes[attribute] = newState[attribute]

			# If we turned off one or more formatting attributes, find the DOM
			# element closest to the root RTF node that got turned off and
			# create a new chain of DOM elements for all the other attributes
			# that are on in the current state.
			if len(turnedOff):

				# Move up beyond the DOM element we need to terminate
				cutoffNodeType = min(turnedOff, key=turnedOff.get)

				while self.__curNode.nodeType != cutoffNodeType:
					self.__curNode = self.__curNode.parent

				self.__curNode = self.__curNode.parent

				# Now, start a new series of DOM elements that will represent the current state
				for attribute in newState:
					if type(newState[attribute]) == bool:
						if newState[attribute]:
							node = elements.DOMElement.getElement(attribute)
							self.__curNode.appendChild(node)
							self.__curNode = node

				textNode = elements.TextElement()
				self.__curNode.appendChild(textNode)
				self.__curNode = textNode

		#####

		def onField(RTFParser, fldinst, fldrslt):

			fieldParts = fldinst.split(' ')

			# If we recognize the field type, we should invoke the appropriate
			# driver.
			if fieldParts[0] in self.__fieldDrivers:
				self.__fieldDrivers[fieldParts[0]](fieldParts[1], fldrslt)

			# If we don't know how to process the field, default to inserting
			# the contents of fldrslt into the current paragraph. Since we're
			# receiving raw RTF, we need to invoke another instance of the DOM
			# class, parse it into a tree, then append that tree to the current
			# paragraph.
			else:
				self.__insertFldrslt(fldrslt)

		#####

		self.__parserCallbacks = {
			'onOpenParagraph': onOpenParagraph,
			'onAppendParagraph': onAppendParagraph,
			'onStateChange': onStateChange,
			'onField': onField
		}

	###########################################################################

	# Returns a dictionary of functions capable of processing various field
	# types. These can be overridden and extended by a call to registerFieldDriver.
	# A field driver is a function that can transform an RTF field into a
	# hierarchy of DOM elements.
	def __initFieldDrivers(self):

		def hyperlinkDriver(fldPara, fldrslt):

			# If the previous text element was empty, it's unnecessary and can
			# be removed to simplify the tree.
			curParNode = self.__curNode.parent
			if 0 == len(self.__curNode.value):
				curParNode.removeChild(self.__curNode)
				self.__curNode = curParNode

			hyperNode = elements.HyperlinkElement()
			hyperNode.attributes['href'] = fldPara[1:len(fldPara) - 1]
			curParNode.appendChild(hyperNode)

			textNode = elements.TextElement()
			hyperNode.appendChild(textNode)
			self.__curNode = textNode

			self.__insertFldrslt(fldrslt)

		#####

		self.__fieldDrivers = {
			'HYPERLINK': hyperlinkDriver
		}

	###########################################################################

	def __init__(self):

		self.__initParserCallbacks()
		self.__initFieldDrivers()

		self.parser = RTFParser({
			'callbacks': self.__parserCallbacks
		})

	###########################################################################

	# Returns a deep copy of the current DOM to allow the client to examine
	# the DOM structure without overwriting the DOMs current state.
	def getTreeNodes(self):

		return copy.deepcopy(self.__rootNode)

	###########################################################################

	# Overrides an existing or adds a new driver for a given field type.
	def registerFieldDriver(self, field, driver):

		self.__fieldDrivers[field] = driver

	###########################################################################

	# Open an RTF from a file.
	def openFile(self, filename):

		self.parser.openFile(filename)

	###########################################################################

	# Open an RTF from a string.
	def openString(self, text):

		self.parser.openString(text)

	###########################################################################

	# Parse the RTF file and populate the DOM.
	def parse(self):

		self.__rootNode = elements.RTFElement()
		self.__curNode = self.__rootNode
		self.parser.parse()

	###########################################################################

	def printTree(self, curNode = None, indent = ''):

		if curNode is None:
			curNode = self.__rootNode

		nodeAttributes = '{'
		for key in curNode.attributes.keys():
			nodeAttributes += "'" + key + "': " + curNode.attributes[key] + ", "
		if len(nodeAttributes) > 1:
			nodeAttributes = nodeAttributes[0:len(nodeAttributes) - 2]
		nodeAttributes += '}'

		print('')
		print(indent + 'nodeType: ' + curNode.nodeType)
		print(indent + 'attributes: ' + nodeAttributes)
		print(indent + 'value: ' + curNode.value)
		print(indent + 'children: ' + str(curNode.childCount()))

		if curNode.children:
			for child in curNode.children:
				self.printTree(child, indent + '\t')

