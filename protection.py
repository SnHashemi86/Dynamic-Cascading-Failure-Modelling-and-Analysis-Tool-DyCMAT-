"""Dynamic cascading protection installation."""

app = None

def set_powerfactory_app(pf_app):
    global app
    app = pf_app

def _get_library_type(folder, pattern, label):
    if folder is None:
        raise RuntimeError(f"Could not access PowerFactory library folder for {label}.")
    matches = folder.GetContents(pattern) or []
    if not matches:
        raise RuntimeError(f"Required PowerFactory type was not found: {pattern}")
    return matches[0]

def _belongs_to_relay(item, relay):
    try:
        return item.fold_id == relay or str(item.fold_id) == str(relay)
    except Exception:
        return False

def _set_if_possible(obj, attribute, value):
    try:
        setattr(obj, attribute, value)
        return True
    except Exception:
        try:
            obj.SetAttribute(attribute, value)
            return True
        except Exception:
            return False

def AddOverloadingProtection(items=None, settings=None):
    settings = settings or {}
    selected_lines = []
    lines = app.GetCalcRelevantObjects("*.ElmLne") or []
    transformers = app.GetCalcRelevantObjects("*.ElmTr2") or []

    if items is None:
        selected_lines = lines
    else:
        requested = set(items)
        selected_lines = [line for line in lines if line.loc_name in requested]

    relay_folder = app.GetLocalLibrary("TypRelay")
    overloading_relay_type = _get_library_type(relay_folder, "F50_F51 Phase overcurrent.TypRelay", "overloading relay")
    ct_folder = app.GetLocalLibrary("TypCt")
    ct_line_type = _get_library_type(ct_folder, "CT.TypCt", "line CT")
    ct_transformer_type = _get_library_type(ct_folder, "CT.TypCt", "transformer CT")

    for i, line in enumerate(selected_lines, start=1):
        if int(line.GetAttribute("outserv")) != 0:
            continue
        print(f"Line {i}: {line.loc_name}")
        cub1 = line.bus1
        cub2 = line.bus2
        relay_name = f"Overloading Relay {line.loc_name}"

        for existing in cub1.GetContents("*.ElmRelay") or []:
            if existing.loc_name in (relay_name, f"Overcurrent Relay {line.loc_name}"):
                existing.Delete()

        relay = cub1.CreateObject("ElmRelay", relay_name)
        relay.typ_id = overloading_relay_type
        ct = relay.CreateObject("StaCT", "CT_OCR")
        ct.typ_id = ct_line_type
        relay.slotupd()

        for logic in app.GetCalcRelevantObjects("*.RelLogdip") or []:
            if _belongs_to_relay(logic, relay):
                logic.pSwitch = [cub1, cub2]

        app.PrintPlain([line, "Overloading Relay Installed"])

    transformer_pickup = float(settings.get("overloading_transformer_pickup", 1.1))
    for i, transformer in enumerate(transformers, start=1):
        if int(transformer.GetAttribute("outserv")) != 0:
            continue
        print(f"Transformer {i}: {transformer.loc_name}")
        cub1 = transformer.bushv
        cub2 = transformer.buslv
        relay_name = f"Overloading TF Relay {transformer.loc_name}"

        for existing in cub1.GetContents("*.ElmRelay") or []:
            if existing.loc_name in (relay_name, f"Overcurrent TF Relay {transformer.loc_name}"):
                existing.Delete()

        relay = cub1.CreateObject("ElmRelay", relay_name)
        relay.typ_id = overloading_relay_type
        ct = relay.CreateObject("StaCT", "CT_OCR")
        ct.typ_id = ct_transformer_type
        relay.slotupd()

        for logic in app.GetCalcRelevantObjects("*.RelLogdip") or []:
            if _belongs_to_relay(logic, relay):
                logic.pSwitch = [cub1, cub2]

        for toc in app.GetCalcRelevantObjects("*.RelToc") or []:
            if _belongs_to_relay(toc, relay) and toc.loc_name == "I>":
                toc.Ipset = transformer_pickup

        app.PrintPlain([transformer, "Overloading Transformer Relay Installed"])

def AddUFLS(items=None, settings=None):
    """Install LFDD_FV relays using user-adjustable UFLS/UVLS stage settings."""
    settings = settings or {}
    stage_defaults = [
        {"enabled": True, "frequency": 49.0, "delay": 0.30, "shed": 10.0},
        {"enabled": True, "frequency": 48.8, "delay": 0.25, "shed": 10.0},
        {"enabled": True, "frequency": 48.6, "delay": 0.20, "shed": 10.0},
        {"enabled": True, "frequency": 48.4, "delay": 0.10, "shed": 10.0},
    ]
    stages = settings.get("ufls_stages") or stage_defaults
    uvls = settings.get("uvls", {"enabled": True, "voltage": 0.8, "delay": 0.5, "shed": 20.0})

    loads = app.GetCalcRelevantObjects("*.ElmLod") or []
    if items is None:
        selected_loads = loads
    else:
        requested = set(items)
        selected_loads = [load for load in loads if load.loc_name in requested]

    relay_folder = app.GetLocalLibrary("TypRelay")
    lfdd_type = _get_library_type(relay_folder, "LFDD_FV.TypRelay", "LFDD/UFLS relay")

    for i, load in enumerate(selected_loads, start=1):
        if int(load.GetAttribute("outserv")) != 0:
            continue
        cub1 = load.bus1
        relay_name = f"LFDD Relay {load.loc_name}"

        for existing in cub1.GetContents("*.ElmRelay") or []:
            if existing.loc_name == relay_name:
                existing.Delete()

        relay = cub1.CreateObject("ElmRelay", relay_name)
        relay.typ_id = lfdd_type
        relay.slotupd()

        for logic in app.GetCalcRelevantObjects("*.RelLslogic") or []:
            if _belongs_to_relay(logic, relay):
                try:
                    if logic.pLoad == [None] or not logic.pLoad:
                        logic.pLoad = [load]
                except Exception:
                    logic.pLoad = [load]

        stage_lookup = {f"{idx} F<": stage for idx, stage in enumerate(stages, start=1)}
        for frq in app.GetCalcRelevantObjects("*.RelFrq") or []:
            if not _belongs_to_relay(frq, relay):
                continue
            stage = stage_lookup.get(frq.loc_name)
            if stage is None:
                continue
            enabled = bool(stage.get("enabled", True))
            _set_if_possible(frq, "outserv", 0 if enabled else 1)
            if enabled:
                frq.Fset = float(stage.get("frequency", 49.0))
                frq.Tdel = float(stage.get("delay", 0.3))

        for ulim in app.GetCalcRelevantObjects("*.RelUlim") or []:
            if _belongs_to_relay(ulim, relay) and ulim.loc_name == "U<":
                enabled = bool(uvls.get("enabled", True))
                _set_if_possible(ulim, "outserv", 0 if enabled else 1)
                if enabled:
                    ulim.Uset = float(uvls.get("voltage", 0.8))
                    ulim.Tdel = float(uvls.get("delay", 0.5))

        logic_lookup = {f"{idx} Logic": stage for idx, stage in enumerate(stages, start=1)}
        for logic in app.GetCalcRelevantObjects("*.RelLslogic") or []:
            if not _belongs_to_relay(logic, relay):
                continue
            if logic.loc_name in logic_lookup:
                stage = logic_lookup[logic.loc_name]
                enabled = bool(stage.get("enabled", True))
                logic.shed = [float(stage.get("shed", 10.0)) if enabled else 0.0]
                _set_if_possible(logic, "outserv", 0 if enabled else 1)
            elif logic.loc_name == "U< Logic":
                enabled = bool(uvls.get("enabled", True))
                logic.shed = [float(uvls.get("shed", 20.0)) if enabled else 0.0]
                _set_if_possible(logic, "outserv", 0 if enabled else 1)

        app.PrintPlain([load, "LFDD Relay Installed"])
        print(f"Load {i} is equipped with LFDD Relay")

def AddOUFGT(items=None, settings=None):
    """Install over/under-frequency generator tripping with adjustable thresholds/delays."""
    settings = settings or {}
    freq = settings.get("generator_frequency", {})
    over_frequency = float(freq.get("over_frequency", 52.0))
    over_delay = float(freq.get("over_delay", 1.0))
    under_frequency = float(freq.get("under_frequency", 48.0))
    under_delay = float(freq.get("under_delay", 1.0))

    generators = (app.GetCalcRelevantObjects("*.ElmSym") or []) + (app.GetCalcRelevantObjects("*.ElmGenstat") or [])
    if items is not None:
        requested = set(items)
        generators = [gen for gen in generators if gen.loc_name in requested]

    relay_folder = app.GetLocalLibrary("TypRelay")
    relay_type = _get_library_type(relay_folder, "F81 Frequency.TypRelay", "generator frequency relay")
    vt_folder = app.GetLocalLibrary("TypVt")
    vt_type = _get_library_type(vt_folder, "VT.TypVt", "VT")

    for i, gen in enumerate(generators, start=1):
        if int(gen.GetAttribute("outserv")) != 0:
            continue

        cub1 = getattr(gen, "bus1", None)
        if cub1 is None:
            print(f"Skipping generator/source '{gen.loc_name}' in OUFGT setup: no bus1 cubicle is assigned.")
            continue

        relay_name = f"OUFGT Relay {gen.loc_name}"
        for existing in cub1.GetContents("*.ElmRelay") or []:
            if existing.loc_name == relay_name:
                existing.Delete()

        relay = cub1.CreateObject("ElmRelay", relay_name)
        relay.typ_id = relay_type
        vt = relay.CreateObject("StaVt", "VolTrans")
        vt.typ_id = vt_type
        relay.slotupd()

        for logic in app.GetCalcRelevantObjects("*.RelLogdip") or []:
            if _belongs_to_relay(logic, relay):
                logic.pSwitch = [cub1]

        for characteristic in (app.GetCalcRelevantObjects("*.RelChar") or []) + (app.GetCalcRelevantObjects("*.RelUlim") or []):
            if not _belongs_to_relay(characteristic, relay):
                continue
            name = characteristic.loc_name
            if name == "F>1":
                characteristic.Ipsetr = over_frequency
                characteristic.Tpset = over_delay
                _set_if_possible(characteristic, "outserv", 0)
            elif name == "F<1":
                characteristic.Ipsetr = under_frequency
                characteristic.Tpset = under_delay
                _set_if_possible(characteristic, "outserv", 0)
            elif name.startswith("F>") or name.startswith("F<"):
                _set_if_possible(characteristic, "outserv", 1)

        app.PrintPlain([gen, "F81 O/U Frequency Relay Installed"])
        print(f"Generator/source {i} is equipped with O/U Frequency Relay")

def AddOVT(items=None, settings=None):
    settings = settings or {}
    voltage = settings.get("voltage_tripping", {})
    threshold = float(voltage.get("over_voltage", 1.2))
    delay = float(voltage.get("over_delay", 1.0))

    generators = (app.GetCalcRelevantObjects("*.ElmSym") or []) + (app.GetCalcRelevantObjects("*.ElmGenstat") or [])
    if items is not None:
        requested = set(items)
        generators = [gen for gen in generators if gen.loc_name in requested]

    relay_folder = app.GetLocalLibrary("TypRelay")
    relay_type = _get_library_type(relay_folder, "F59 Phase overvoltage.TypRelay", "over-voltage relay")
    vt_folder = app.GetLocalLibrary("TypVt")
    vt_type = _get_library_type(vt_folder, "VT.TypVt", "VT")

    for gen in generators:
        if int(gen.GetAttribute("outserv")) != 0:
            continue

        cub1 = getattr(gen, "bus1", None)
        if cub1 is None:
            print(f"Skipping generator/source '{gen.loc_name}' in over-voltage setup: no bus1 cubicle is assigned.")
            continue

        relay_name = f"OVol Relay {gen.loc_name}"
        for existing in cub1.GetContents("*.ElmRelay") or []:
            if existing.loc_name == relay_name:
                existing.Delete()

        relay = cub1.CreateObject("ElmRelay", relay_name)
        relay.typ_id = relay_type
        vt = relay.CreateObject("StaVt", "VolTrans")
        vt.typ_id = vt_type
        relay.slotupd()

        for logic in app.GetCalcRelevantObjects("*.RelLogdip") or []:
            if _belongs_to_relay(logic, relay):
                logic.pSwitch = [cub1]

        for char in app.GetCalcRelevantObjects("*.RelChar") or []:
            if not _belongs_to_relay(char, relay):
                continue
            if char.loc_name in ("Upn>", "Upp>"):
                char.Ipset = threshold
                char.Tpset = delay
                _set_if_possible(char, "outserv", 0)
            elif char.loc_name.startswith("Upn>>") or char.loc_name.startswith("Upp>>"):
                _set_if_possible(char, "outserv", 1)

        app.PrintPlain([gen, "F59 Over-Voltage Relay Installed"])

def AddUVT(items=None, settings=None):
    settings = settings or {}
    voltage = settings.get("voltage_tripping", {})
    threshold = float(voltage.get("under_voltage", 0.75))
    delay = float(voltage.get("under_delay", 1.0))

    generators = (app.GetCalcRelevantObjects("*.ElmSym") or []) + (app.GetCalcRelevantObjects("*.ElmGenstat") or [])
    if items is not None:
        requested = set(items)
        generators = [gen for gen in generators if gen.loc_name in requested]

    relay_folder = app.GetLocalLibrary("TypRelay")
    relay_type = _get_library_type(relay_folder, "F27 Phase undervoltage.TypRelay", "under-voltage relay")
    vt_folder = app.GetLocalLibrary("TypVt")
    vt_type = _get_library_type(vt_folder, "VT.TypVt", "VT")

    for gen in generators:
        if int(gen.GetAttribute("outserv")) != 0:
            continue

        cub1 = getattr(gen, "bus1", None)
        if cub1 is None:
            print(f"Skipping generator/source '{gen.loc_name}' in under-voltage setup: no bus1 cubicle is assigned.")
            continue

        relay_name = f"UVol Relay {gen.loc_name}"
        for existing in cub1.GetContents("*.ElmRelay") or []:
            if existing.loc_name == relay_name:
                existing.Delete()

        relay = cub1.CreateObject("ElmRelay", relay_name)
        relay.typ_id = relay_type
        vt = relay.CreateObject("StaVt", "VolTrans")
        vt.typ_id = vt_type
        relay.slotupd()

        for logic in app.GetCalcRelevantObjects("*.RelLogdip") or []:
            if _belongs_to_relay(logic, relay):
                logic.pSwitch = [cub1]

        for char in app.GetCalcRelevantObjects("*.RelChar") or []:
            if not _belongs_to_relay(char, relay):
                continue
            if char.loc_name in ("Upn<", "Upp<"):
                char.Ipset = threshold
                char.Tpset = delay
                _set_if_possible(char, "outserv", 0)
            elif char.loc_name.startswith("Upn<<") or char.loc_name.startswith("Upp<<"):
                _set_if_possible(char, "outserv", 1)

        app.PrintPlain([gen, "F27 Under-Voltage Relay Installed"])
