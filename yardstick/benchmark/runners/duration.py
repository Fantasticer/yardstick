# Copyright 2014: Mirantis Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

# yardstick comment: this is a modified copy of
# rally/rally/benchmark/runners/constant.py

"""A runner that runs a specific time before it returns
"""

from __future__ import absolute_import
import os
import multiprocessing
import logging
import traceback
import time

from yardstick.benchmark.runners import base

LOG = logging.getLogger(__name__)


def _worker_process(queue, cls, method_name, scenario_cfg,
                    context_cfg, aborted, output_queue):

    sequence = 1

    runner_cfg = scenario_cfg['runner']

    interval = runner_cfg.get("interval", 1)
    duration = runner_cfg.get("duration", 60)
    LOG.info("Worker START, duration is %ds", duration)
    LOG.debug("class is %s", cls)

    runner_cfg['runner_id'] = os.getpid()

    benchmark = cls(scenario_cfg, context_cfg)
    benchmark.setup()
    method = getattr(benchmark, method_name)

    sla_action = None
    if "sla" in scenario_cfg:
        sla_action = scenario_cfg["sla"].get("action", "assert")

    start = time.time()
    while True:

        LOG.debug("runner=%(runner)s seq=%(sequence)s START",
                  {"runner": runner_cfg["runner_id"], "sequence": sequence})

        data = {}
        errors = ""

        try:
            result = method(data)
        except AssertionError as assertion:
            # SLA validation failed in scenario, determine what to do now
            if sla_action == "assert":
                raise
            elif sla_action == "monitor":
                LOG.warning("SLA validation failed: %s", assertion.args)
                errors = assertion.args
        except Exception as e:
            errors = traceback.format_exc()
            LOG.exception(e)
        else:
            if result:
                output_queue.put(result)

        time.sleep(interval)

        benchmark_output = {
            'timestamp': time.time(),
            'sequence': sequence,
            'data': data,
            'errors': errors
        }

        queue.put(benchmark_output)

        LOG.debug("runner=%(runner)s seq=%(sequence)s END",
                  {"runner": runner_cfg["runner_id"], "sequence": sequence})

        sequence += 1

        if (errors and sla_action is None) or \
                (time.time() - start > duration or aborted.is_set()):
            LOG.info("Worker END")
            break

    benchmark.teardown()


class DurationRunner(base.Runner):
    """Run a scenario for a certain amount of time

If the scenario ends before the time has elapsed, it will be started again.

  Parameters
    duration - amount of time the scenario will be run for
        type:    int
        unit:    seconds
        default: 1 sec
    interval - time to wait between each scenario invocation
        type:    int
        unit:    seconds
        default: 1 sec
    """
    __execution_type__ = 'Duration'

    def _run_benchmark(self, cls, method, scenario_cfg, context_cfg):
        self.process = multiprocessing.Process(
            target=_worker_process,
            args=(self.result_queue, cls, method, scenario_cfg,
                  context_cfg, self.aborted, self.output_queue))
        self.process.start()
