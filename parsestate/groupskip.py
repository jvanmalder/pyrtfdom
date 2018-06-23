# -*- coding: utf-8 -*-

class GroupSkipState(ParseState):

	def __init__(self, parser):

		self.parser._setStateValue('groupSkip', True, False)
		super().__init__(parser)

	###########################################################################

	# Look out for when we've finished with the skipped group.
	def _parseCloseBrace(self):

		super()._parseCloseBrace(False)

		# Once we've finished skipping over the group, we can stop parsing in
		# this state.
		if 'groupSkip' not in self.parser.fullState:
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

