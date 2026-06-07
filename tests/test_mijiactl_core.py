import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

from mijiactl.capabilities import CapabilityStore
from mijiactl.client import Device, FakeMijiaApi, MijiaClient, login_auth
from mijiactl.cli import run_cli
from mijiactl.package_skill import export_skill_package
from mijiactl.miot_spec import fetch_model_spec
from mijiactl.policy import CommandPolicy, MijiaError
from mijiactl.snapshots import SnapshotStore
from mijiactl.values import parse_value


class ValueParsingTests(unittest.TestCase):
    def test_parse_value_converts_common_scalar_strings(self):
        self.assertIs(parse_value("true"), True)
        self.assertIs(parse_value("false"), False)
        self.assertEqual(parse_value("26"), 26)
        self.assertEqual(parse_value("26.5"), 26.5)
        self.assertEqual(parse_value("quick wash"), "quick wash")


class CapabilityStoreTests(unittest.TestCase):
    def test_action_name_resolves_to_siid_and_aiid_from_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = CapabilityStore(Path(tmp))
            store.write_model(
                "washer.model",
                {
                    "model": "washer.model",
                    "properties": [],
                    "actions": [{"name": "start-wash", "siid": 2, "aiid": 2}],
                },
            )

            action = store.resolve_action("washer.model", "start-wash")

            self.assertEqual(action, {"name": "start-wash", "siid": 2, "aiid": 2})

    def test_package_style_methods_are_normalized_for_properties_and_actions(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = CapabilityStore(Path(tmp))
            store.write_model(
                "fan.model",
                {
                    "model": "fan.model",
                    "properties": [{"name": "on", "method": {"siid": 2, "piid": 1}}],
                    "actions": [{"name": "start", "method": {"siid": 2, "aiid": 1}}],
                },
            )

            prop = store.resolve_property("fan.model", "on")
            action = store.resolve_action("fan.model", "start")

            self.assertEqual(prop, {"name": "on", "siid": 2, "piid": 1})
            self.assertEqual(action, {"name": "start", "siid": 2, "aiid": 1})

    def test_miot_spec_fetcher_maps_model_to_instance(self):
        urls = []

        def fake_fetch(url):
            urls.append(url)
            if "instances" in url:
                return {
                    "instances": [
                        {
                            "model": "dmaker.fan.p5",
                            "type": "urn:miot-spec-v2:device:fan:0000A005:dmaker-p5:1",
                        }
                    ]
                }
            return {"type": "urn:miot-spec-v2:device:fan:0000A005:dmaker-p5:1", "services": []}

        spec = fetch_model_spec("dmaker.fan.p5", fetch_json=fake_fetch)

        self.assertEqual(spec["model"], "dmaker.fan.p5")
        self.assertEqual(len(urls), 2)

    def test_unknown_action_raises_action_not_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = CapabilityStore(Path(tmp))
            store.write_model("washer.model", {"model": "washer.model", "properties": [], "actions": []})

            with self.assertRaises(MijiaError) as raised:
                store.resolve_action("washer.model", "start-wash")

            self.assertEqual(raised.exception.code, "ACTION_NOT_FOUND")


class PolicyTests(unittest.TestCase):
    def test_offline_device_is_rejected(self):
        policy = CommandPolicy()
        device = Device(did="1", name="Washer", model="washer.model", online=False, room="Balcony")

        with self.assertRaises(MijiaError) as raised:
            policy.ensure_device_can_execute(device)

        self.assertEqual(raised.exception.code, "DEVICE_OFFLINE")

    def test_multiple_fuzzy_matches_returns_candidates_without_execution(self):
        policy = CommandPolicy()
        devices = [
            Device(did="1", name="Bedroom Lamp", model="lamp.model", online=True, room="Bedroom"),
            Device(did="2", name="Bedside Lamp", model="lamp.model", online=True, room="Bedroom"),
        ]

        with self.assertRaises(MijiaError) as raised:
            policy.resolve_device(devices, "bed")

        self.assertEqual(raised.exception.code, "AMBIGUOUS_DEVICE")
        self.assertEqual([candidate["did"] for candidate in raised.exception.data["candidates"]], ["1", "2"])

    def test_high_risk_action_requires_confirmation_token(self):
        policy = CommandPolicy()
        device = Device(did="1", name="Washer", model="washer.model", online=True, room="Balcony")

        with self.assertRaises(MijiaError) as raised:
            policy.ensure_action_allowed(device, "start-wash", confirm=None)

        self.assertEqual(raised.exception.code, "CONFIRMATION_REQUIRED")
        self.assertIn("confirm", raised.exception.data)

    def test_disabled_device_policy_blocks_control(self):
        policy = CommandPolicy({"disabled_devices": [{"did": "1"}]})
        device = Device(did="1", name="Washer", model="washer.model", online=True, room="Balcony")

        with self.assertRaises(MijiaError) as raised:
            policy.ensure_device_can_execute(device)

        self.assertEqual(raised.exception.code, "POLICY_BLOCKED")

    def test_configured_confirm_required_pattern_blocks_without_token(self):
        policy = CommandPolicy({"confirm_required": [{"model": "plug", "action": "set-on"}]})
        device = Device(did="1", name="Plug", model="chuangmi.plug.m1", online=True, room="Kitchen")

        with self.assertRaises(MijiaError) as raised:
            policy.ensure_action_allowed(device, "set-on", confirm=None)

        self.assertEqual(raised.exception.code, "CONFIRMATION_REQUIRED")


class CliTests(unittest.TestCase):
    def test_version_command_reports_runtime_version_without_auth(self):
        output = run_cli(["version"])

        payload = json.loads(output)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["name"], "mijiactl")
        self.assertRegex(payload["data"]["version"], r"^\d+\.\d+\.\d+$")
        self.assertIn("config_dir", payload["data"])

    def test_setup_guides_first_time_auth(self):
        with tempfile.TemporaryDirectory() as tmp:
            auth_file = Path(tmp) / "auth.json"

            output = run_cli(["setup"], auth_path=auth_file)

            payload = json.loads(output)
            self.assertTrue(payload["ok"])
            self.assertIn("mijiactl login", payload["data"]["next_steps"])

    def test_setup_skips_login_when_auth_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            auth_file = Path(tmp) / "auth.json"
            auth_file.write_text('{"serviceToken":"secret-token"}', encoding="utf-8")
            config_file = Path(tmp) / "config.json"

            output = run_cli(["setup"], auth_path=auth_file, config_path=config_file)

            payload = json.loads(output)
            self.assertTrue(payload["ok"])
            self.assertNotIn("mijiactl login", payload["data"]["next_steps"])
            self.assertIn("mijiactl config init", payload["data"]["next_steps"])

    def test_doctor_reports_next_steps_when_auth_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            auth_file = Path(tmp) / "auth.json"

            output = run_cli(["doctor"], auth_path=auth_file)

            payload = json.loads(output)
            self.assertTrue(payload["ok"])
            self.assertIn("mijiactl login", payload["data"]["next_steps"])

    def test_set_uses_mijiaapi_list_based_property_api(self):
        class ListPropertyApi(FakeMijiaApi):
            def __init__(self):
                super().__init__(
                    devices=[{"did": "1", "name": "Lamp", "model": "lamp.model", "isOnline": True}],
                    device_infos={
                        "lamp.model": {
                            "model": "lamp.model",
                            "properties": [{"name": "on", "siid": 2, "piid": 1}],
                            "actions": [],
                        }
                    },
                )
                self.set_batches = []

            def set_devices_prop(self, data):
                self.set_batches.append(data)
                return [{"code": 0}]

        with tempfile.TemporaryDirectory() as tmp:
            api = ListPropertyApi()
            output = run_cli(
                ["set", "--did", "1", "--prop", "on", "--value", "true"],
                client=MijiaClient(api),
                store=CapabilityStore(Path(tmp)),
                snapshots=SnapshotStore(Path(tmp) / "snapshots"),
            )

            payload = json.loads(output)
            self.assertTrue(payload["ok"])
            self.assertEqual(api.set_batches, [[{"did": "1", "siid": 2, "piid": 1, "value": True}]])

    def test_scene_commands_use_real_mijiaapi_home_id_shape(self):
        class SceneApi(FakeMijiaApi):
            def __init__(self):
                super().__init__()
                self.list_home_ids = []
                self.run_calls = []

            def get_scenes_list(self, home_id=None):
                self.list_home_ids.append(home_id)
                return [
                    {
                        "scene_id": "scene-1",
                        "name": "All lights off",
                        "home_id": home_id,
                        "enable": True,
                        "scene_action": {"secret": "do not expose"},
                    }
                ]

            def run_scene(self, scene_id, home_id):
                self.run_calls.append((scene_id, home_id))
                return True

        with tempfile.TemporaryDirectory() as tmp:
            api = SceneApi()
            list_output = run_cli(
                ["scene", "list", "--home-id", "home-1"],
                client=MijiaClient(api),
                snapshots=SnapshotStore(Path(tmp)),
            )
            run_output = run_cli(
                ["scene", "run", "--id", "scene-1", "--home-id", "home-1", "--confirm", "scene:scene-1"],
                client=MijiaClient(api),
                snapshots=SnapshotStore(Path(tmp)),
            )

        self.assertTrue(json.loads(list_output)["ok"])
        self.assertTrue(json.loads(run_output)["ok"])
        self.assertNotIn("do not expose", list_output)
        self.assertEqual(json.loads(list_output)["data"]["scenes"][0]["scene_id"], "scene-1")
        self.assertEqual(api.list_home_ids, ["home-1"])
        self.assertEqual(api.run_calls, [("scene-1", "home-1")])

    def test_homes_command_exposes_home_ids_for_scene_commands(self):
        class HomesApi(FakeMijiaApi):
            def get_homes_list(self):
                return [
                    {
                        "id": "home-1",
                        "name": "Home",
                        "address": "secret address",
                        "longitude": 1.0,
                        "latitude": 2.0,
                        "roomlist": [{"id": "room-1", "name": "Bedroom", "dids": ["1"]}],
                    }
                ]

        with tempfile.TemporaryDirectory() as tmp:
            output = run_cli(["homes", "--json"], client=MijiaClient(HomesApi()), snapshots=SnapshotStore(Path(tmp)))

        payload = json.loads(output)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["homes"][0]["id"], "home-1")
        self.assertEqual(payload["data"]["homes"][0]["rooms"][0]["name"], "Bedroom")
        self.assertNotIn("secret address", output)
        self.assertNotIn("longitude", output)

    def test_info_falls_back_to_mijiaapi_devices_module(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls = []
            fake_package = types.ModuleType("mijiaAPI")
            fake_devices = types.ModuleType("mijiaAPI.devices")

            def fake_get_device_info(model):
                calls.append(model)
                return {"model": model, "services": [{"iid": 2, "actions": [{"iid": 1, "description": "Start"}]}]}

            fake_devices.get_device_info = fake_get_device_info
            old_package = sys.modules.get("mijiaAPI")
            old_devices = sys.modules.get("mijiaAPI.devices")
            sys.modules["mijiaAPI"] = fake_package
            sys.modules["mijiaAPI.devices"] = fake_devices
            try:
                output = run_cli(
                    ["info", "--model", "fan.model", "--json"],
                    client=MijiaClient(FakeMijiaApi()),
                    store=CapabilityStore(Path(tmp)),
                    snapshots=SnapshotStore(Path(tmp) / "snapshots"),
                )
            finally:
                if old_package is not None:
                    sys.modules["mijiaAPI"] = old_package
                else:
                    sys.modules.pop("mijiaAPI", None)
                if old_devices is not None:
                    sys.modules["mijiaAPI.devices"] = old_devices
                else:
                    sys.modules.pop("mijiaAPI.devices", None)

            payload = json.loads(output)
            self.assertTrue(payload["ok"])
            self.assertEqual(calls, ["fan.model"])
            self.assertEqual(payload["data"]["actions"][0]["name"], "start")

    def test_action_uses_run_action_after_capability_resolution(self):
        with tempfile.TemporaryDirectory() as tmp:
            api = FakeMijiaApi(
                devices=[{"did": "1", "name": "Washer", "model": "washer.model", "isOnline": True, "room": "Balcony"}],
                device_infos={
                    "washer.model": {
                        "model": "washer.model",
                        "properties": [],
                        "actions": [{"name": "start-wash", "siid": 2, "aiid": 2}],
                    }
                },
            )
            client = MijiaClient(api)

            output = run_cli(
                ["action", "--did", "1", "--action", "start-wash", "--confirm", "start-wash"],
                client=client,
                store=CapabilityStore(Path(tmp)),
                snapshots=SnapshotStore(Path(tmp) / "snapshots"),
                policy=CommandPolicy(),
            )

            payload = json.loads(output)
            self.assertTrue(payload["ok"])
            self.assertEqual(api.actions_run, [{"did": "1", "siid": 2, "aiid": 2}])

    def test_action_passes_args_as_miot_action_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            api = FakeMijiaApi(
                devices=[{"did": "1", "name": "Speaker", "model": "speaker.model", "isOnline": True}],
                device_infos={
                    "speaker.model": {
                        "model": "speaker.model",
                        "properties": [],
                        "actions": [{"name": "play-text", "siid": 5, "aiid": 1}],
                    }
                },
            )

            output = run_cli(
                ["action", "--did", "1", "--action", "play-text", "--arg", "我是 codex"],
                client=MijiaClient(api),
                store=CapabilityStore(Path(tmp)),
                snapshots=SnapshotStore(Path(tmp) / "snapshots"),
            )

            payload = json.loads(output)
            self.assertTrue(payload["ok"])
            self.assertEqual(api.actions_run, [{"did": "1", "siid": 5, "aiid": 1, "in": ["我是 codex"]}])

    def test_devices_command_returns_agent_consumable_json(self):
        api = FakeMijiaApi(
            devices=[{"did": "1", "name": "Lamp", "model": "lamp.model", "isOnline": True, "room": "Bedroom"}]
        )

        with tempfile.TemporaryDirectory() as tmp:
            output = run_cli(["devices", "--json"], client=MijiaClient(api), snapshots=SnapshotStore(Path(tmp)))

        payload = json.loads(output)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["devices"][0]["name"], "Lamp")

    def test_devices_command_uses_fresh_snapshot_without_refetching(self):
        class CountingApi(FakeMijiaApi):
            def __init__(self):
                super().__init__(devices=[{"did": "1", "name": "Lamp", "model": "lamp.model", "isOnline": True}])
                self.device_calls = 0

            def get_devices_list(self):
                self.device_calls += 1
                return super().get_devices_list()

        with tempfile.TemporaryDirectory() as tmp:
            api = CountingApi()
            snapshots = SnapshotStore(Path(tmp), now=lambda: 1000)

            first = run_cli(["devices", "--json"], client=MijiaClient(api), snapshots=snapshots)
            second = run_cli(["devices", "--json"], client=MijiaClient(api), snapshots=snapshots)

            self.assertTrue(json.loads(first)["ok"])
            payload = json.loads(second)
            self.assertTrue(payload["ok"])
            self.assertEqual(api.device_calls, 1)
            self.assertTrue(payload["data"]["cache"]["hit"])

    def test_devices_refresh_bypasses_snapshot(self):
        class CountingApi(FakeMijiaApi):
            def __init__(self):
                super().__init__(devices=[{"did": "1", "name": "Lamp", "model": "lamp.model", "isOnline": True}])
                self.device_calls = 0

            def get_devices_list(self):
                self.device_calls += 1
                return super().get_devices_list()

        with tempfile.TemporaryDirectory() as tmp:
            api = CountingApi()
            snapshots = SnapshotStore(Path(tmp), now=lambda: 1000)

            run_cli(["devices", "--json"], client=MijiaClient(api), snapshots=snapshots)
            output = run_cli(["devices", "--refresh", "--json"], client=MijiaClient(api), snapshots=snapshots)

            payload = json.loads(output)
            self.assertTrue(payload["ok"])
            self.assertEqual(api.device_calls, 2)
            self.assertFalse(payload["data"]["cache"]["hit"])

    def test_stale_device_snapshot_refreshes_after_ttl(self):
        now = 1000

        class CountingApi(FakeMijiaApi):
            def __init__(self):
                super().__init__(devices=[{"did": "1", "name": "Lamp", "model": "lamp.model", "isOnline": True}])
                self.device_calls = 0

            def get_devices_list(self):
                self.device_calls += 1
                return super().get_devices_list()

        with tempfile.TemporaryDirectory() as tmp:
            api = CountingApi()
            snapshots = SnapshotStore(Path(tmp), ttl_seconds=10, now=lambda: now)

            run_cli(["devices", "--json"], client=MijiaClient(api), snapshots=snapshots)
            now = 1011
            output = run_cli(["devices", "--json"], client=MijiaClient(api), snapshots=snapshots)

            payload = json.loads(output)
            self.assertTrue(payload["ok"])
            self.assertEqual(api.device_calls, 2)
            self.assertFalse(payload["data"]["cache"]["hit"])

    def test_control_command_resolves_device_from_snapshot_without_refetching_devices(self):
        class CountingApi(FakeMijiaApi):
            def __init__(self):
                super().__init__(
                    devices=[{"did": "1", "name": "Lamp", "model": "lamp.model", "isOnline": True}],
                    device_infos={
                        "lamp.model": {
                            "model": "lamp.model",
                            "properties": [{"name": "on", "siid": 2, "piid": 1}],
                            "actions": [],
                        }
                    },
                )
                self.device_calls = 0

            def get_devices_list(self):
                self.device_calls += 1
                return super().get_devices_list()

            def get_devices_prop(self, data):
                return [{"code": 0, "value": True}]

        with tempfile.TemporaryDirectory() as tmp:
            api = CountingApi()
            snapshots = SnapshotStore(Path(tmp), now=lambda: 1000)
            store = CapabilityStore(Path(tmp) / "capabilities")

            run_cli(["devices", "--json"], client=MijiaClient(api), snapshots=snapshots)
            output = run_cli(["get", "--did", "1", "--prop", "on"], client=MijiaClient(api), store=store, snapshots=snapshots)

            payload = json.loads(output)
            self.assertTrue(payload["ok"])
            self.assertEqual(api.device_calls, 1)

    def test_homes_and_scene_list_use_snapshots(self):
        class CountingApi(FakeMijiaApi):
            def __init__(self):
                super().__init__()
                self.home_calls = 0
                self.scene_calls = 0

            def get_homes_list(self):
                self.home_calls += 1
                return [{"id": "home-1", "name": "Home", "roomlist": []}]

            def get_scenes_list(self, home_id=None):
                self.scene_calls += 1
                return [{"scene_id": "scene-1", "name": "Lights off", "home_id": home_id, "enable": True}]

        with tempfile.TemporaryDirectory() as tmp:
            api = CountingApi()
            snapshots = SnapshotStore(Path(tmp), now=lambda: 1000)

            run_cli(["homes", "--json"], client=MijiaClient(api), snapshots=snapshots)
            run_cli(["homes", "--json"], client=MijiaClient(api), snapshots=snapshots)
            run_cli(["scene", "list", "--home-id", "home-1"], client=MijiaClient(api), snapshots=snapshots)
            run_cli(["scene", "list", "--home-id", "home-1"], client=MijiaClient(api), snapshots=snapshots)

            self.assertEqual(api.home_calls, 1)
            self.assertEqual(api.scene_calls, 1)

    def test_doctor_reports_auth_presence_without_secret_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            auth_file = Path(tmp) / "auth.json"
            auth_file.write_text('{"serviceToken":"secret-token","userId":"123"}', encoding="utf-8")

            output = run_cli(["doctor"], auth_path=auth_file)

            payload = json.loads(output)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["data"]["auth"]["present"], True)
            self.assertEqual(payload["data"]["auth"]["key_count"], 2)
            self.assertTrue(payload["data"]["auth"]["required_keys"]["serviceToken"])
            self.assertNotIn("secret-token", output)

    def test_login_command_saves_auth_path_and_redacts_auth_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            auth_file = Path(tmp) / "auth.json"
            calls = []

            class LoginApi:
                def __init__(self, auth_data_path=None):
                    calls.append(auth_data_path)

                def login(self):
                    auth_file.write_text('{"serviceToken":"secret-token","userId":"123"}', encoding="utf-8")
                    return {"serviceToken": "secret-token", "userId": "123"}

            output = login_auth(auth_file, api_factory=LoginApi)

            payload = json.loads(output)
            self.assertTrue(payload["ok"])
            self.assertEqual(calls, [str(auth_file)])
            self.assertEqual(payload["data"]["auth"]["present"], True)
            self.assertEqual(payload["data"]["auth"]["key_count"], 2)
            self.assertNotIn("secret-token", output)

    def test_parser_errors_are_returned_as_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = run_cli(
                ["scene", "run", "--id", "scene-1"],
                client=MijiaClient(FakeMijiaApi()),
                snapshots=SnapshotStore(Path(tmp)),
            )

        payload = json.loads(output)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "ARGUMENT_ERROR")

    def test_scene_run_requires_confirmation_by_default(self):
        class SceneApi(FakeMijiaApi):
            def run_scene(self, scene_id, home_id):
                raise AssertionError("scene should not run without confirmation")

        with tempfile.TemporaryDirectory() as tmp:
            output = run_cli(
                ["scene", "run", "--id", "scene-1", "--home-id", "home-1"],
                client=MijiaClient(SceneApi()),
                snapshots=SnapshotStore(Path(tmp)),
            )

        payload = json.loads(output)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "CONFIRMATION_REQUIRED")

    def test_unexpected_runtime_errors_are_returned_as_json(self):
        class BrokenApi(FakeMijiaApi):
            def get_devices_list(self):
                raise ValueError("boom")

        with tempfile.TemporaryDirectory() as tmp:
            output = run_cli(["devices", "--json"], client=MijiaClient(BrokenApi()), snapshots=SnapshotStore(Path(tmp)))

        payload = json.loads(output)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "UNEXPECTED_ERROR")
        self.assertIn("boom", payload["error"]["message"])

    def test_info_lookup_failures_return_capability_lookup_failed(self):
        with tempfile.TemporaryDirectory() as tmp:
            class BrokenInfoApi(FakeMijiaApi):
                def get_device_info(self, model):
                    raise ValueError("bad spec page")

            output = run_cli(
                ["info", "--model", "fan.model", "--json"],
                client=MijiaClient(BrokenInfoApi()),
                store=CapabilityStore(Path(tmp)),
                snapshots=SnapshotStore(Path(tmp) / "snapshots"),
            )

            payload = json.loads(output)
            self.assertFalse(payload["ok"])
            self.assertEqual(payload["error"]["code"], "CAPABILITY_LOOKUP_FAILED")
            self.assertIn("fan.model", payload["error"]["message"])

    def test_real_client_initialization_passes_auth_path_to_mijiaapi_v3(self):
        with tempfile.TemporaryDirectory() as tmp:
            auth_file = Path(tmp) / "auth.json"
            auth_file.write_text('{"serviceToken":"secret-token"}', encoding="utf-8")
            calls = []

            class FakeRealApi:
                available = True

                def __init__(self, auth_data_path=None):
                    calls.append(auth_data_path)

            fake_module = types.ModuleType("mijiaAPI")
            fake_module.mijiaAPI = FakeRealApi
            old_lower = sys.modules.pop("mijiaapi", None)
            old_upper = sys.modules.get("mijiaAPI")
            sys.modules["mijiaAPI"] = fake_module
            try:
                MijiaClient(auth_path=auth_file)
            finally:
                if old_lower is not None:
                    sys.modules["mijiaapi"] = old_lower
                if old_upper is not None:
                    sys.modules["mijiaAPI"] = old_upper
                else:
                    sys.modules.pop("mijiaAPI", None)

            self.assertEqual(calls, [str(auth_file)])
            self.assertNotIsInstance(calls[0], dict)


class PackageSkillTests(unittest.TestCase):
    def test_repo_contains_npx_skills_compatible_skill_directory(self):
        skill_dir = Path("skills") / "controlling-mijia-smart-home"

        self.assertFalse(Path("SKILL.md").exists())
        self.assertTrue(Path("LICENSE").exists())
        self.assertTrue(Path("THIRD_PARTY_NOTICES.md").exists())
        self.assertTrue((skill_dir / "SKILL.md").exists())
        self.assertTrue((skill_dir / "references" / "setup.md").exists())
        self.assertTrue((skill_dir / "references" / "safety.md").exists())

    def test_repo_contains_maintainer_evals_for_agent_regression(self):
        evals_file = Path("evals") / "evals.json"

        payload = json.loads(evals_file.read_text(encoding="utf-8"))

        self.assertGreaterEqual(len(payload), 5)
        self.assertTrue(any(item["id"] == "washer_start_action" for item in payload))
        self.assertTrue(any(item["id"] == "first_time_windows_setup" for item in payload))

    def test_export_skill_package_creates_distributable_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "controlling-mijia-smart-home"

            manifest = export_skill_package(target)

            self.assertEqual(manifest["skill"], "controlling-mijia-smart-home")
            self.assertTrue((target / "SKILL.md").exists())
            self.assertTrue((target / "references" / "setup.md").exists())
            self.assertTrue((target / "references" / "safety.md").exists())
            self.assertTrue((target / "install.ps1").exists())
            self.assertTrue((target / "README.zh-CN.md").exists())


if __name__ == "__main__":
    unittest.main()
