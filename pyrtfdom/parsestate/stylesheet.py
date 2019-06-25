# -*- coding: utf-8 -*-

from ..tokentype import TokenType
from .state import ParseState

class StylesheetState(ParseState):

	def __init__(self, parser):

		super().__init__(parser)
		self._parser._setStateValue('private', 'inStylesheet', True)

	###########################################################################

	# Inserts the currently parsed style into the stylesheet.
	def __insertStyle(self):

		if 'groupSkip' not in self._parser._fullState['private'] and 'styleName' in self._parser._curState['private'] and 'styleType' in self._parser._curState['private'] and 'styleIndex' in self._parser._curState['private'] and 'styleProperties' in self._parser._curState['private']:
			self._parser._insertStyle(self._parser._curState['private']['styleType'], self._parser._curState['private']['styleIndex'], {'name': self._parser._curState['private']['styleName'], 'attributes': self._parser._curState['private']['styleProperties']})

	###########################################################################

	# Once we're done parsing the stylesheet, make sure to update the document's
	# default properties if they're defined.
	def __updateDefaults(self):

		defaultParagraphStyles = self._parser._getStyle('paragraph', 0)
		if defaultParagraphStyles:
			self._parser._updateDefaultAttributes('paragraph', defaultParagraphStyles, True)

	###########################################################################

	# Look out for when we've finished with the skipped group.
	def _parseCloseBrace(self):

		retVal = True

		# Once we've finished skipping over the group, we can stop parsing in
		# this state.
		if 'inStylesheet' not in self._parser._fullState['private']:
			self.__updateDefaults()
			retVal = False

		# We're inserting a newly parsed style into the stylesheet
		else:
			self.__insertStyle()

		super()._parseCloseBrace(False)
		return retVal

	###########################################################################

	# Do nothing...
	def _parseControl(self, word, param):

		# If we're in the middle of a style that's invalidly formatted, skip it
		# in the hopes that the rest of the document is okay.
		if 'groupSkip' not in self._parser._fullState['private']:

			# We're defining a new style definition
			if TokenType.OPEN_BRACE == self._parser._prevToken[0]:

				# Paragraph style
				if TokenType.OPEN_BRACE == self._parser._prevToken[0] and '\\s' == word:
					self._parser._setStateValue('private', 'styleType', 'paragraph')
					self._parser._setStateValue('private', 'styleIndex', param)

				# Need to look ahead one extra token to see what kind of style we're
				# dealing with
				elif TokenType.OPEN_BRACE == self._parser._prevToken[0] and '\\*' == word:

					self._parser._prevToken = self._parser._curToken
					self._parser._curToken = self._getNextToken()

					if TokenType.EOF == self._parser._curToken[0]:
						raise EOFError('Premature EOF encountered when parsing RTF stylesheet')

					tokenParts = self._splitControlWord(self._parser._curToken)

					# Section style
					if '\\ds' == tokenParts[0]:
						self._parser._setStateValue('private', 'styleType', 'section')
						self._parser._setStateValue('private', 'styleIndex', tokenParts[1])

					# Table style
					elif '\\ts' == tokenParts[0]:
						self._parser._setStateValue('private', 'styleType', 'table')
						self._parser._setStateValue('private', 'styleIndex', tokenParts[1])

					# Character style
					elif '\\cs' == tokenParts[0]:
						self._parser._setStateValue('private', 'styleType', 'character')
						self._parser._setStateValue('private', 'styleIndex', tokenParts[1])

					# Style definition is invalid, so skip over it and hope for the best
					else:
						self._parser._setStateValue('private', 'groupSkip', True)

				# Style definition is invalid, so skip over it and hope for the best
				else:
					self._parser._setStateValue('private', 'groupSkip', True)

			# We're parsing a style definition's format
			elif 'styleType' in self._parser._curState['private']:

				styleProperties = {}
				if 'styleProperties' in self._parser._curState['private']:
					styleProperties = self._parser._curState['private']['styleProperties']

				if 'section' == self._parser._curState['private']['styleType']:
					# TODO
					return True

				elif 'table' == self._parser._curState['private']['styleType']:
					# TODO
					return True

				elif 'paragraph' == self._parser._curState['private']['styleType']:

					# Page break before paragraph
					if '\\pagebb' == word:
						styleProperties['pagebreakBefore'] = True

					# Paragraph alignment
					elif '\\ql' == word:
						styleProperties['alignment'] = 'left'

					elif '\\qr' == word:
						styleProperties['alignment'] = 'right'

					elif '\\qc' == word:
						styleProperties['alignment'] = 'center'

					elif '\\qd' == word:
						styleProperties['alignment'] = 'distributed'

					elif '\\qj' == word:
						styleProperties['alignment'] = 'justified'

					elif '\\qt' == word:
						styleProperties['alignment'] = 'thai-distributed'

					# TODO: how do I want to handle \qkN alignment? Will require
					# setting two attributes.

				elif 'character' == self._parser._curState['private']['styleType']:

					# Italic
					if '\\i' == word:
						if param is None or '1' == param:
							styleProperties['italic'] = True
						else:
							styleProperties['italic'] = False

					# Bold
					elif '\\b' == word:
						if param is None or '1' == param:
							styleProperties['bold'] = True
						else:
							styleProperties['bold'] = False

					# Underline
					elif '\\ul' == word:
						if param is None or '1' == param:
							styleProperties['underline'] = True
						else:
							styleProperties['underline'] = False

					# Strike-through
					elif '\\strike' == word:
						if param is None or '1' == param:
							styleProperties['strikethrough'] = True
						else:
							styleProperties['strikethrough'] = False

					# TODO: how do I want to handle \plain?

					# Foreground color
					elif '\\cf' == word and isinstance(param, str) and param.isdigit():
						color = self._parser._getColor(param)
						if color:
							styleProperties['fColor'] = color

					# Background color
					elif '\\cb' == word and isinstance(param, str) and param.isdigit():
						color = self._parser._getColor(param)
						if color:
							styleProperties['bColor'] = color

				self._parser._setStateValue('private', 'styleProperties', styleProperties)

			# Style definition is invalid, so skip over it and hope for the best
			else:
				self._parser._setStateValue('private', 'groupSkip', True)

		return True

	###########################################################################

	# We're parsing the style definition's name
	def _parseCharacter(self, token):

		if 'groupSkip' not in self._parser._fullState['private'] and ';' != token and '\n' != token:
			styleName = ''
			if 'styleName' in self._parser._curState['private']:
				styleName = self._parser._curState['private']['styleName']
			styleName += token
			self._parser._setStateValue('private', 'styleName', styleName)

		return True

