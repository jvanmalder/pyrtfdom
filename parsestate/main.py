# -*- coding: utf-8 -*-

from ..tokentype import TokenType

from .state import ParseState
from .groupskip import GroupSkipState
from .pict import PictState
from .field import FieldState
from .stylesheet import StylesheetState

class MainState(ParseState):

	def _parseControl(self, word, param):

		if (
			# TODO: We'll treat the value of \*\generator as a document attribute.
			'\*' == self._parser._prevToken[1] and word == '\\generator'
		) or (
			# Proprietary to LibreOffice / OpenOffice, and I can't even find
			# documentation for what it's supposed to do, so just skip over it.
			'\*' == self._parser._prevToken[1] and word == '\\pgdsctbl'
		) or (
			# Math properties. For now, we're skipping over this.
			'\*' == self._parser._prevToken[1] and word == '\\mmathPr'
		) or (
			# User-defined document properties. For now, we're skipping over
			# this too.
			'\*' == self._parser._prevToken[1] and word == '\\userprops'
		) or (
			# Revision tracking. Not going to deal with this.
			'\*' == self._parser._prevToken[1] and word == '\\revtbl'
		) or (
			# A newer form of revision tracking.
			'\*' == self._parser._prevToken[1] and word == '\\rsidtbl'
		) or (
			# Only exists when a document contains subdocuments. Not going to
			# deal with this.
			'\*' == self._parser._prevToken[1] and word == '\\filetbl'
		) or (
			# Not going to do anything with lists for now.
			'\*' == self._parser._prevToken[1] and word == '\\listtable'
		) or (
			'\*' == self._parser._prevToken[1] and word == '\\listoverridetable'
		) or (
			# Skip over these sections. We're not going to use them (at least
			# for now.)
			TokenType.OPEN_BRACE == self._parser._prevToken[0] and (
				word == '\\fonttbl' or
				word == '\\colortbl' or
				word == '\\stylerestrictions' or # Does this even exist...?
				word == '\\info' # TODO: parse this into document attributes
			)
		):
			state = GroupSkipState(self._parser)
			state.parse()
			return True

		# We're parsing the stylesheet
		elif TokenType.OPEN_BRACE == self._parser._prevToken[0] and '\\stylesheet' == word:
			state = StylesheetState(self._parser)
			state.parse()
			return True

		# Beginning of a field
		elif TokenType.OPEN_BRACE == self._parser._prevToken[0] and '\\field' == word:
			state = FieldState(self._parser)
			state.parse()
			return True

		# We've entered an embedded image.
		elif TokenType.OPEN_BRACE == self._parser._prevToken[0] and '\\pict' == word:
			state = PictState(self._parser)
			state.parse()
			return True

		else:
			return super()._parseControl(word, param)

	###########################################################################

	def _parseCharacter(self, token):

		if '\n' != token:
			self._parser._appendToCurrentParagraph(token)

		return True

