# Copyright (c) 2022 Robert Bosch GmbH and Microsoft Corporation
#
# This program and the accompanying materials are made available under the
# terms of the Apache License, Version 2.0 which is available at
# https://www.apache.org/licenses/LICENSE-2.0.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# SPDX-License-Identifier: Apache-2.0

import asyncio
import json
import logging
import signal

from vehicle import Vehicle, vehicle  # type: ignore
from velocitas_sdk.util.log import (  # type: ignore
    get_opentelemetry_log_factory,
    get_opentelemetry_log_format,
)
from velocitas_sdk.vdb.reply import DataPointReply
from velocitas_sdk.vehicle_app import VehicleApp, subscribe_topic

# Configure the VehicleApp logger with the necessary log config and level.
logging.setLogRecordFactory(get_opentelemetry_log_factory())
logging.basicConfig(format=get_opentelemetry_log_format())
logging.getLogger().setLevel("DEBUG")
logger = logging.getLogger(__name__)

SET_CRASH_EVENT_TOPIC = "crashdetect/crashed"
SET_CRASH_RESPONSE_TOPIC = "crashdetect/crashed/response"


class CrashDetectApp(VehicleApp):
    def __init__(self, vehicle_client: Vehicle):
        super().__init__()
        self.Vehicle = vehicle_client

    async def on_start(self):
        await self.Vehicle.ADAS.ObstacleDetection.IsWarning.subscribe(
            self.on_distance_change
        )
        await self.Vehicle.Acceleration.Longitudinal.subscribe(self.on_accel_change)

    async def on_distance_change(self, data: DataPointReply):
        distance = data.get(self.Vehicle.ADAS.ObstacleDetection.IsWarning).value
        logger.info(distance)
        if distance:
            await self.set_crash_event(1)

    async def on_accel_change(self, data: DataPointReply):
        accel = data.get(self.Vehicle.Acceleration.Longitudinal).value
        logger.info(accel)
        if (accel < -50) or (50 < accel):
            logger.info(accel)
            await self.set_crash_event(1)

    async def set_crash_event(self, status):
        await self.publish_event(
            SET_CRASH_EVENT_TOPIC,
            json.dumps(
                {
                    "result": {
                        "status": status,
                    },
                }
            ),
        )

    @subscribe_topic(SET_CRASH_RESPONSE_TOPIC)
    async def on_crash_event_response_received(self, data: str) -> None:
        await self.set_crash_event(0)


async def main():
    """Main function"""
    logger.info("Starting CrashDetectApp...")
    vehicle_app = CrashDetectApp(vehicle)
    await vehicle_app.run()


LOOP = asyncio.get_event_loop()
LOOP.add_signal_handler(signal.SIGTERM, LOOP.stop)
LOOP.run_until_complete(main())
LOOP.close()
