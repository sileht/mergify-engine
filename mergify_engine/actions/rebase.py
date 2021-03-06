# -*- encoding: utf-8 -*-
#
#  Copyright © 2019–2021 Mergify SAS
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import voluptuous

from mergify_engine import actions
from mergify_engine import branch_updater
from mergify_engine import check_api
from mergify_engine import config
from mergify_engine import context
from mergify_engine import rules
from mergify_engine.rules import types


class RebaseAction(actions.Action):
    is_command = True

    always_run = True

    silent_report = True

    validator = {
        voluptuous.Required("bot_account", default=None): voluptuous.Any(
            None, types.Jinja2
        ),
    }

    async def run(
        self, ctxt: context.Context, rule: rules.EvaluatedRule
    ) -> check_api.Result:
        if not config.GITHUB_APP:
            return check_api.Result(
                check_api.Conclusion.FAILURE,
                "Unavailable with GitHub Action",
                "Due to GitHub Action limitation, the `rebase` command is only available "
                "with the Mergify GitHub App.",
            )

        if await ctxt.is_behind:
            if await ctxt.github_workflow_changed():
                return check_api.Result(
                    check_api.Conclusion.ACTION_REQUIRED,
                    "Pull request must be rebased manually.",
                    "GitHub App like Mergify are not allowed to rebase pull request where `.github/workflows` is changed.",
                )

            output = branch_updater.pre_rebase_check(ctxt)
            if output:
                return output

            try:
                await branch_updater.rebase_with_git(ctxt, self.config["bot_account"])
                return check_api.Result(
                    check_api.Conclusion.SUCCESS,
                    "Branch has been successfully rebased",
                    "",
                )
            except (
                branch_updater.AuthenticationFailure,
                branch_updater.BranchUpdateFailure,
            ) as e:
                return check_api.Result(
                    check_api.Conclusion.FAILURE, "Branch rebase failed", str(e)
                )
        else:
            return check_api.Result(
                check_api.Conclusion.SUCCESS, "Branch already up to date", ""
            )
