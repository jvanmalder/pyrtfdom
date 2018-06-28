# -*- coding: utf-8 -*-

from ..tokentype import TokenType
from .state import ParseState

class GroupSkipState(ParseState):

	def __init__(self, parser):

		super().__init__(parser)
		self._parser._setStateValue('private', 'groupSkip', True)

	###########################################################################

	# Look out for when we've finished with the skipped group.
	def _parseCloseBrace(self):

		super()._parseCloseBrace(False)

		# Once we've finished skipping over the group, we can stop parsing in
		# this state.
		if 'groupSkip' not in self._parser._fullState['private']:
			return False
		else:
			return True

	###########################################################################

	# Do nothing...
	def _parseControl(self, word, param):

		return True

	###########################################################################

	# Do nothing...
	def _parseCharacter(self, token):

		return True

