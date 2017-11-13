# -*- coding: utf-8 -*-

class DOMElement(object):

	def __init__(self, nodeType):

		self.__parent = None
		self._nodeType = nodeType
		self._children = []

		# The node's value and attributes
		self.value = ''
		self.attributes = {}

	###########################################################################

	# Read-only property that identifies the node's type
	@property
	def nodeType(self):

		return self._nodeType

	###########################################################################

	# Read-only direct access to node's children.
	@property
	def children(self):

		return self._children

	###########################################################################

	# Identifies the parent node
	@property
	def parent(self):

		return self.__parent

	@parent.setter
	def parent(self, p):

		if p is not None and not issubclass(p.__class__, DOMElement):
			raise ValueError('Parent must inherit from the DOMElement type.')

		self.__parent = p

	###########################################################################

	# Append a node to another node's children.
	def appendChild(self, child):

		if list is type(self._children):
			self._children.append(child)
			child.parent = self

		else:
			raise Exception('Children not allowed for node type ' + self.nodeType)

	###########################################################################

	# Removes the passed node from another node's children.
	def removeChild(self, child):

		if list is type(self.children):
			self.children.remove(child)
			child.parent = None

	###########################################################################

	# Returns the number of child nodes.
	def childCount(self):

		try:
			return len(self._children)
		except TypeError:
			return 0

	###########################################################################

	# Return a new DOM element of the specified type.
	@staticmethod
	def getElement(elemType):

		if 'rtf' == elemType:
			return RTFElement()

		elif 'text' == elemType:
			return TextElement()

		elif 'para' == elemType:
			return ParaElement()

		elif 'hyperlink' == elemType:
			return HyperlinkElement()

		elif 'bold' == elemType:
			return BoldElement()

		elif 'italic' == elemType:
			return ItalicElement()

		elif 'underline' == elemType:
			return UnderlineElement()

		elif 'strikethrough' == elemType:
			return StrikethroughElement()

		else:
			raise Exception(elemType + ' is an unsupported Element type.')

###############################################################################
###############################################################################

# Root RTF node
class RTFElement(DOMElement):

	def __init__(self):

		super().__init__('rtf')

###############################################################################
###############################################################################

# Text
class TextElement(DOMElement):

	def __init__(self):

		super().__init__('text')

		# Children aren't allowed in a text node
		self._children = False

###############################################################################
###############################################################################

# Paragraph
class ParaElement(DOMElement):

	def __init__(self):

		super().__init__('para')

###############################################################################
###############################################################################

# Bold
class BoldElement(DOMElement):

	def __init__(self):

		super().__init__('bold')

###############################################################################
###############################################################################

# Italic
class ItalicElement(DOMElement):

	def __init__(self):

		super().__init__('italic')

###############################################################################
###############################################################################

# Underline
class UnderlineElement(DOMElement):

	def __init__(self):

		super().__init__('underline')

###############################################################################
###############################################################################

# Strikethrough
class StrikethroughElement(DOMElement):

	def __init__(self):

		super().__init__('strikethrough')

###############################################################################
###############################################################################

# Hyperlink
class HyperlinkElement(DOMElement):

	def __init__(self):

		super().__init__('hyperlink')

