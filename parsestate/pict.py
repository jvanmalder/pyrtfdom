# -*- coding: utf-8 -*-

from ..tokentype import TokenType
from .state import ParseState

class PictState(ParseState):

	def __init__(self, parser):

		super().__init__(parser)

		self._parser._setStateValue('inPict', True, False)
		self._parser._setStateValue('pictAttributes', {}, False)

		# Initialize image data and ID
		self.__data = ''
		self.__blipUIDBuffer = '' # used for parsing integer ID
		self.__blipUID = False # contains the actual integer ID

	###########################################################################

	# Process a \pict embedded image. For now, this only supports the default
	# hex dump format.
	def __append(self, pictAttributes):

		# TODO: data protection access scheme, GGG!
		if 'onImage' in self.__options['callbacks']:
			self.__options['callbacks']['onImage'](self._parser, pictAttributes, binascii.unhexlify(self.__data))

	###########################################################################

	# Look out for when we've finished with the embedded image.
	def _parseCloseBrace(self):

		oldFullState = self._parser.fullState
		super()._parseCloseBrace(False)

		# We're finished parsing an image ID (other possible source of ID is
		# the bliptag control word.)
		if 'inBlipUID' in oldFullState and oldFullState['inBlipUID']:
			self.__blipUID = int(self.__blipUIDBuffer.lstrip('0'), 16)

		# Once we've finished with the pict group, we can stop parsing in this
		# state.
		elif 'inPict' not in self._parser.fullState:
			self.__append(oldFullState['pictAttributes'])
			return False
		else:
			return True

	###########################################################################

	def _parseControl(self, word, param):

		# We'll encounter this destination when parsing images. It's a way to
		# uniquely identify the image. In my experience with test data, blipuid
		# and bliptagN are different representations of the same value.
		if '\\*' == self._parser._prevToken[1] and '\\blipuid' == word:

			# We already got the ID in a simpler way, so we can skip over this destination
			if self.__blipUID:
				state = SkipGroupState()
				state.parse()

			# We haven't gotten the ID yet, so go ahead and parse this destination
			else:
				self._parser._setStateValue('inBlipUID', True, False)

			return True

		# This is the other (easier) way to uniquely identify an image
		elif '\\bliptag' == word:
			self.__blipUID = int(param, 10)
			return True

		# Various image formatting parameters and metadata
		elif 'pictAttributes' in self._parser.curState and word in [
			'\\picscalex',    # Horizontal scaling %
			'\\picscaley',    # Vertical scaling %
			'\\piccropl',     # Twips (1/1440 of an inch) to crop off the left
			'\\piccropr',     # Twips (1/1440 of an inch) to crop off the right
			'\\piccropt',     # Twips (1/1440 of an inch) to crop off the top
			'\\piccropb',     # Twips (1/1440 of an inch) to crop off the bottom
			'\\picw',         # Width in pixels (if image is bitmap or from QuickDraw)
			'\\pich',         # Height in pixels (if image is bitmap or from QuickDraw)
			'\\picwgoal',     # Desired width in twips (1/1440 of an inch)
			'\\pichgoal',     # Desired height in twips (1/1440 of an inch)
			'\\picbpp',       # Specifies the bits per pixel in a metafile bitmap.
			                  # The valid range is 1 through 32, with 1, 4, 8, and
			                  # 24 being recognized.

			# These apply only to Windows bitmap images
			'\\wbmbitspixel', # From the 1.9.1 spec: "Number of adjacent color bits
			                  # on each plane needed to define a pixel. Possible
			                  # values are 1 (monochrome), 4 (16 colors), 8
			                  # (256 colors) and 24 (RGB). The default value is 1."
			'\\wbmplanes',    # From the 1.9.1 spec: "Number of bitmap color planes
			                  # (must equal 1)."
			'\\wbmwidthbytes' # From the 1.9.1 spec: "Specifies the number of bytes
			                  # in each raster line. This value must be an even
			                  # number because the Windows Graphics Device Interface
			                  # (GDI) assumes that the bit values of a bitmap form
			                  # an array of integer (two-byte) values. In other
			                  # words, \wbmwidthbytes multiplied by 8 must be the
			                  # next multiple of 16 greater than or equal to the
			                  # \picw (bitmap width in pixels) value.
		]:
			pictAttributes = self._parser.curState['pictAttributes']
			pictAttributes[word] = int(param, 10)
			self._parser._setStateValue('pictAttributes', pictAttributes, False)
			return True

		# JPG
		elif 'pictAttributes' in self._parser.curState and '\\jpegblip' == word:
			pictAttributes = self._parser.curState['pictAttributes']
			pictAttributes['source'] = 'jpeg'
			self._parser._setStateValue('pictAttributes', pictAttributes, False)
			return True

		# PNG
		elif 'pictAttributes' in self._parser.curState and '\\pngblip' == word:
			pictAttributes = self._parser.curState['pictAttributes']
			pictAttributes['source'] = 'png'
			self._parser._setStateValue('pictAttributes', pictAttributes, False)
			return True

		# EMF (Enhanced metafile)
		elif 'pictAttributes' in self._parser.curState and '\\emfblip' == word:
			pictAttributes = self._parser.curState['pictAttributes']
			pictAttributes['source'] = 'emf'
			self._parser._setStateValue('pictAttributes', pictAttributes, False)
			return True

		# OS/2 metafile
		elif 'pictAttributes' in self._parser.curState and '\\pmmetafile' == word:
			pictAttributes = self._parser.curState['pictAttributes']
			pictAttributes['source'] = 'os2meta'
			pictAttributes['metafileType'] = param
			self._parser._setStateValue('pictAttributes', pictAttributes, False)
			return True

		# Windows metafile
		elif 'pictAttributes' in self._parser.curState and '\\wmetafile' == word:
			pictAttributes = self._parser.curState['pictAttributes']
			pictAttributes['source'] = 'winmeta'
			pictAttributes['metafileMappingMode'] = param
			self._parser._setStateValue('pictAttributes', pictAttributes, False)
			return True

		# Windows device-independent bitmap
		elif 'pictAttributes' in self._parser.curState and '\\dibitmap' == word:
			pictAttributes = self._parser.curState['pictAttributes']
			pictAttributes['source'] = 'wdibmp'
			pictAttributes['bitmapType'] = param
			self._parser._setStateValue('pictAttributes', pictAttributes, False)
			return True

		# Windows device-dependent bitmap
		elif 'pictAttributes' in self._parser.curState and '\\wbitmap' == word:
			pictAttributes = self._parser.curState['pictAttributes']
			pictAttributes['source'] = 'wddbmp'
			pictAttributes['bitmapType'] = param
			self._parser._setStateValue('pictAttributes', pictAttributes, False)
			return True

		else:
			return super()._parseControl(word, param)

	###########################################################################

	def _parseCharacter(self, token):

		if 'inBlipUID' in self._parser.curState and self._parser.curState['inBlipUID']:
			self.__blipUIDBuffer += token

		elif not token.isspace():
			self.__data += token

