# -*- coding: utf-8 -*-

import copy

from pyrtfdom import elements
from pyrtfdom.parse import RTFParser

class RTFDOM(object):

	# Read-only property that returns the current node.
	@property
	def curNode(self):

		return self.__curNode

	###########################################################################

	# Read-only property that returns the root node.
	@property
	def rootNode(self):

		return self.__rootNode

	###########################################################################

	# Utility function that parses an RTF snippet and returns its DOM tree.
	@staticmethod
	def parseSubRTF(rtfString):

		subTree = RTFDOM()
		subTree.openString(rtfString)
		subTree.parse()

		return subTree.getTreeNodes()

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

	# Initializes the parser callbacks that are used to construct the DOM.
	def __initParserCallbacks(self):

		# Utility function for the below callbacks that sets up a series of nodes
		# corresponding to the specified format.
		def __setFormatNodes(RTFParser, curParNode, state):

			for attribute in state:
				if RTFParser.isAttributeFormat(attribute):
					if type(state[attribute]) == bool:
						if state[attribute]:
							node = elements.DOMElement.getElement(attribute)
							self.__curNode.appendChild(node)
							self.__curNode = node
					else:
						curParNode.attributes[attribute] = state[attribute]

		#####

		# Inserts a page break into the current paragraph node.
		def onPageBreak(RTFParser):

			# First, walk up to the current paragraph node
			while 'para' != self.__curNode.nodeType:
				self.__curNode = self.__curNode.parent

			# Second, create and append the page break node
			node = elements.PageBreakElement()
			self.__curNode.appendChild(node)

			# Finally, restore the current formatting state in the same paragraph
			# and append to it a new text node. Create a new text node to append
			# any text that might be in the same paragraph.
			__setFormatNodes(RTFParser, self.__curNode, RTFParser.fullState)
			textNode = elements.TextElement()
			self.__curNode.appendChild(textNode)
			self.__curNode = textNode

		#####

		# Create a new paragraph and apply any styles that apply in the current
		# state.
		def onOpenParagraph(RTFParser):

			# Create the paragraph node
			para = elements.ParaElement()
			self.__rootNode.appendChild(para)
			self.__curNode = para

			# Any formatting attributes that are turned on in the current state
			# should be represented by their corresponding DOM elements
			__setFormatNodes(RTFParser, para, RTFParser.fullState)

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
			if fieldParts[0] in self.__fieldDriverOverrides:
				self.__fieldDriverOverrides[fieldParts[0]](self, fieldParts[1], fldrslt)
			elif fieldParts[0] in self.__fieldDrivers:
				self.__fieldDrivers[fieldParts[0]](self, fieldParts[1], fldrslt)

			# If we don't know how to process the field, default to inserting
			# the contents of fldrslt into the current paragraph. Since we're
			# receiving raw RTF, we need to invoke another instance of the DOM
			# class, parse it into a tree, then append that tree to the current
			# paragraph.
			else:
				self.insertFldrslt(fldrslt)

		#####

		def onImage(RTFParser, attributes, image):

			# First, walk up to the first non-text node
			while 'text' == self.__curNode.nodeType:
				self.__curNode = self.__curNode.parent

			# Second, create and append the image node
			node = elements.ImageElement()
			node.value = image
			for attribute in attributes.keys():
				node.attributes[attribute] = attributes[attribute]

			self.__curNode.appendChild(node)

			# Finally, create a new text node to append any text that might be
			# in the same paragraph.
			textNode = elements.TextElement()
			self.__curNode.appendChild(textNode)
			self.__curNode = textNode

		#####

		self.__parserCallbacks = {
			'onPageBreak': onPageBreak,
			'onOpenParagraph': onOpenParagraph,
			'onAppendParagraph': onAppendParagraph,
			'onStateChange': onStateChange,
			'onField': onField,
			'onImage': onImage
		}

	###########################################################################

	# Returns a dictionary of functions capable of processing various field
	# types. These can be overridden and extended by a call to registerFieldDriver.
	# A field driver is a function that can transform an RTF field into a
	# hierarchy of DOM elements.
	def __initFieldDrivers(self):

		def hyperlinkDriver(dom, fldPara, fldrslt):

			curParNode = dom.curNode.parent

			# If the previous text element was empty, it's unnecessary and can
			# be removed to simplify the tree.
			if 0 == len(dom.curNode.value):
				dom.removeCurNode()

			hyperNode = elements.HyperlinkElement()
			hyperNode.attributes['href'] = fldPara[1:len(fldPara) - 1]
			curParNode.appendChild(hyperNode)

			textNode = elements.TextElement()
			hyperNode.appendChild(textNode)
			dom.__curNode = textNode

			dom.insertFldrslt(fldrslt)

		#####

		self.__fieldDrivers = {
			'HYPERLINK': hyperlinkDriver
		}

		# This is where drivers that override built-in defaults are registered.
		self.__fieldDriverOverrides = {}

	###########################################################################

	def __init__(self):

		self.reset()

		# Will reference the RTF Parser with custom callbacks
		self.parser = None

		self.__initParserCallbacks()
		self.__initFieldDrivers()

		self.parser = RTFParser({
			'callbacks': self.__parserCallbacks
		})

	###########################################################################

	# Resets the DOM parser to an initialized state. Allows us to parse another
	# document.
	def reset(self):

		# The head and current position in the DOM, respectively
		self.__rootNode = None
		self.__curNode = None

	###########################################################################

	# Removes the current node and sets the new current node to its parent.
	# This shouldn't be used very often, but is useful for implementing custom
	# field types.
	def removeCurNode(self):

		curParNode = self.__curNode.parent
		curParNode.removeChild(self.__curNode)
		self.__curNode = curParNode

	###########################################################################

	# Inserts a new empty text element into the specified parent element and
	# sets it as the new current element.
	def initTextElement(self, parent):

		# Append a new text element after the contents of fldrslt so we can
		# continue appending text to the current paragraph.
		textNode = elements.TextElement()
		parent.appendChild(textNode)
		self.__curNode = textNode

	###########################################################################

	# Appends the contents of a fldrslt RTF paragraph into the current paragraph.
	# I decided not to make this private, because a custom field handler needs
	# to be able to call this, but this really shouldn't be called for any other
	# reason.
	def insertFldrslt(self, rtfString):

		curParNode = self.__curNode.parent

		# If the previous text element was empty, it's unnecessary and can be
		# removed to simplify the tree.
		if 0 == len(self.__curNode.value):
			curParNode.removeChild(self.__curNode)
			self.__curNode = curParNode

		subDOM = RTFDOM.parseSubRTF('{' + rtfString + '}')
		paraNode = subDOM.children[0]

		for child in paraNode.children:
			curParNode.appendChild(child)

		# Append a new text element after the contents of fldrslt so we can
		# continue appending text to the current paragraph.
		self.initTextElement(curParNode)

	###########################################################################

	# Returns a deep copy of the current DOM to allow the client to examine
	# the DOM structure without overwriting the DOMs current state.
	def getTreeNodes(self):

		return copy.deepcopy(self.__rootNode)

	###########################################################################

	# Overrides an existing or adds a new driver for a given field type.
	def registerFieldDriver(self, field, driver):

		if self.__fieldDrivers[field]:
			self.__fieldDriverOverrides[field] = driver
		else:
			self.__fieldDrivers[field] = driver

	###########################################################################

	# Manually runs an original field driver, even if an override exists. A
	# little hacky, but this allows us to conditionally call the original
	# driver from a newer overriding driver. If the driver doesn't exist, we'll
	# just copy in the fldrslt text.
	def runDefaultFieldDriver(self, driver, fldPara, fldrslt):

		if self.__fieldDrivers[driver]:
			self.__fieldDrivers[driver](self, fldPara, fldrslt)
		else:
			self.insertFldrslt(fldrslt)

	###########################################################################

	# Open an RTF from a file.
	def openFile(self, filename):

		self.reset()
		self.parser.openFile(filename)

	###########################################################################

	# Open an RTF from a string.
	def openString(self, text):

		self.reset()
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
			nodeAttributes += "'" + key + "': " + str(curNode.attributes[key]) + ", "
		if len(nodeAttributes) > 1:
			nodeAttributes = nodeAttributes[0:len(nodeAttributes) - 2]
		nodeAttributes += '}'

		if isinstance(curNode.value, (bytes, bytearray)):
			nodeValue = '<Binary Data>'
		else:
			nodeValue = curNode.value

		print('')
		print(indent + 'nodeType: ' + curNode.nodeType)
		print(indent + 'attributes: ' + nodeAttributes)
		print(indent + 'value: ' + nodeValue)
		print(indent + 'children: ' + str(curNode.childCount()))

		if curNode.children:
			for child in curNode.children:
				self.printTree(child, indent + '\t')

