"""PowerFactory connection, initialization, RMS simulation, and system inventory."""

import os
import importlib
from collections import defaultdict
from pathlib import Path

from common import safe_float, object_full_name

_DLL_HANDLES = []

def configure_powerfactory_environment(pf_python_path: str):
    """
    Add the selected PowerFactory Python folder and likely DLL folders to the
    runtime search paths. This is particularly useful for a PyInstaller build.
    """
    if not pf_python_path:
        raise ValueError("PowerFactory Python API path is empty.")

    python_dir = Path(pf_python_path)
    if not python_dir.exists():
        raise FileNotFoundError(f"PowerFactory Python API path does not exist: {python_dir}")

    python_dir_str = str(python_dir)
    if python_dir_str not in sys.path:
        sys.path.insert(0, python_dir_str)

    pf_root = python_dir.parent.parent
    dll_candidates = [pf_root, pf_root / "bin"]

    for candidate in dll_candidates:
        if not candidate.exists():
            continue
        candidate_str = str(candidate)
        current_path = os.environ.get("PATH", "")
        path_parts = current_path.split(os.pathsep) if current_path else []
        if candidate_str not in path_parts:
            os.environ["PATH"] = candidate_str + os.pathsep + current_path

        if hasattr(os, "add_dll_directory"):
            try:
                handle = os.add_dll_directory(candidate_str)
                _DLL_HANDLES.append(handle)
            except OSError:
                pass

def connect_powerfactory(pf_python_path: str):
    configure_powerfactory_environment(pf_python_path)

    pf = importlib.import_module("powerfactory")
    pf_app = pf.GetApplication()

    if pf_app is None:
        raise RuntimeError(
            "Could not connect to DIgSILENT PowerFactory. Check that PowerFactory "
            "is installed/licensed, the selected API path is correct, and DyCMAT "
            "uses the same Python architecture/version required by PowerFactory."
        )

    try:
        pf_app.Show()
    except Exception:
        pass

    return pf_app, pf

def find_study_case_recursive(study_folder, target_name: str, log_func=None):
    target_name = target_name.strip().lower()
    study_cases = study_folder.GetContents("*.IntCase", 1) or []

    if log_func:
        log_func("")
        log_func("Available study cases found:")

    selected_case = None
    for case in study_cases:
        if log_func:
            log_func(f"  - {case.loc_name}")
        if case.loc_name.strip().lower() == target_name:
            selected_case = case

    return selected_case

def activate_project_and_optional_case(pf_app, project_name: str, study_case_name: str = "", log_func=None):
    project = pf_app.ActivateProject(project_name)
    if project is None:
        raise RuntimeError(f"Could not activate project: {project_name}")

    if log_func:
        log_func(f"Activated project: {project_name}")

    if not study_case_name.strip():
        if log_func:
            log_func("No study-case name entered. Using the currently active study case in PowerFactory.")
        return project, None

    study_folder = pf_app.GetProjectFolder("study")
    if study_folder is None:
        raise RuntimeError("Could not find Study Cases folder.")

    selected_case = find_study_case_recursive(study_folder, study_case_name, log_func)
    if selected_case is None:
        raise RuntimeError(
            f"Study case not found: {study_case_name}\n"
            "Copy the exact study-case name from the log, or leave the field blank "
            "to use the currently active study case in PowerFactory."
        )

    selected_case.Activate()
    if log_func:
        log_func(f"Activated study case: {selected_case.loc_name}")

    return project, selected_case

def run_initialization_only(pf_app, simulation_type="0", log_func=None):
    init_cmd = pf_app.GetFromStudyCase("ComInc")
    if init_cmd is None:
        raise RuntimeError("ComInc was not found in the active study case.")

    init_cmd.iopt_sim = simulation_type
    if log_func:
        log_func("Running initialization ...")
        log_func(f"ComInc.iopt_sim = {simulation_type}")

    error = init_cmd.Execute()
    if error != 0:
        raise RuntimeError(f"Initialization failed. PowerFactory error code: {error}")

    if log_func:
        log_func("Initialization completed successfully.")

def Run_Dynamic_Simulation(pf_app, simulation_type, simulation_time, log_func=None, post_init_callback=None):
    init_cmd = pf_app.GetFromStudyCase("ComInc")
    sim_cmd = pf_app.GetFromStudyCase("ComSim")

    if init_cmd is None:
        raise RuntimeError("ComInc was not found in the active study case.")
    if sim_cmd is None:
        raise RuntimeError("ComSim was not found in the active study case.")

    output_window = pf_app.GetOutputWindow()
    init_cmd.iopt_sim = simulation_type
    sim_cmd.tstop = simulation_time

    if log_func:
        log_func("Running RMS/dynamic simulation ...")
        log_func(f"ComInc.iopt_sim = {simulation_type}")
        log_func(f"ComSim.tstop = {simulation_time}")

    init_error = init_cmd.Execute()
    if init_error != 0:
        raise RuntimeError(f"Initialization failed. PowerFactory error code: {init_error}")

    if post_init_callback is not None:
        post_init_callback()

    output_window.Clear()
    sim_error = sim_cmd.Execute()
    if sim_error != 0:
        raise RuntimeError(f"RMS/dynamic simulation failed. PowerFactory error code: {sim_error}")

    if log_func:
        log_func("RMS/dynamic simulation completed successfully.")

    return output_window

def get_total_load_generation(pf_app):
    """Preserve the original network-total calculation while avoiding division by zero."""
    nets = pf_app.GetCalcRelevantObjects("*.ElmNet") or []
    if not nets:
        return 0.0, 0.0

    total_load = 0.0
    total_gen = 0.0
    load_hits = 0
    gen_hits = 0

    for net in nets:
        try:
            total_load += float(net.GetAttribute("c:Pload"))
            load_hits += 1
        except Exception:
            pass
        try:
            total_gen += float(net.GetAttribute("c:Pgen"))
            gen_hits += 1
        except Exception:
            pass

    if load_hits:
        total_load /= load_hits
    if gen_hits:
        total_gen /= gen_hits
    return total_load, total_gen

def _get_attribute_first(obj, candidates):
    for attr in candidates:
        try:
            value = obj.GetAttribute(attr)
            if value is not None:
                return value
        except Exception:
            pass
        try:
            value = getattr(obj, attr)
            if value is not None:
                return value
        except Exception:
            pass
    return None

def _cubicle_terminal_name(cubicle):
    if cubicle is None:
        return "—"
    try:
        terminal = cubicle.cterm
        if terminal is not None:
            return str(terminal.loc_name)
    except Exception:
        pass
    try:
        terminal = cubicle.GetAttribute("cterm")
        if terminal is not None:
            return str(terminal.loc_name)
    except Exception:
        pass
    return str(getattr(cubicle, "loc_name", "—"))

def _element_status(obj):
    try:
        return "Out of service" if int(obj.GetAttribute("outserv")) else "In service"
    except Exception:
        try:
            return "Out of service" if int(obj.outserv) else "In service"
        except Exception:
            return "Unknown"

def _read_p_q(obj, category):
    if category == "Loads":
        p_candidates = ["m:Psum:bus1", "m:P:bus1", "plini"]
        q_candidates = ["m:Qsum:bus1", "m:Q:bus1", "qlini"]
    elif category in ("Synchronous Generators", "Other Sources"):
        p_candidates = ["m:P:bus1", "m:Psum:bus1", "pgini", "Pgen"]
        q_candidates = ["m:Q:bus1", "m:Qsum:bus1", "qgini", "Qgen"]
    else:
        p_candidates = ["m:P:bus1", "m:Psum:bus1"]
        q_candidates = ["m:Q:bus1", "m:Qsum:bus1"]

    return safe_float(_get_attribute_first(obj, p_candidates)), safe_float(_get_attribute_first(obj, q_candidates))

def collect_system_inventory(pf_app):
    """
    Collect a post-initialization inventory for the GUI. Numeric line indices are
    deterministic and are the same indices accepted by Excel contingency mode.
    """
    category_specs = [
        ("Lines", "*.ElmLne"),
        ("Loads", "*.ElmLod"),
        ("Synchronous Generators", "*.ElmSym"),
        ("Other Sources", "*.ElmGenstat"),
        ("Other Sources", "*.ElmPvsys"),
        ("Other Sources", "*.ElmAsm"),
        ("Other Sources", "*.ElmXnet"),
        ("Transformers", "*.ElmTr2"),
    ]

    raw = defaultdict(list)
    seen_full_names = set()

    for category, pattern in category_specs:
        for obj in pf_app.GetCalcRelevantObjects(pattern) or []:
            full_name = object_full_name(obj)
            if full_name in seen_full_names:
                continue
            seen_full_names.add(full_name)
            raw[category].append(obj)

    for category in raw:
        raw[category].sort(key=lambda x: (str(getattr(x, "loc_name", "")).lower(), object_full_name(x).lower()))

    rows = []
    for category in ["Lines", "Loads", "Synchronous Generators", "Other Sources", "Transformers"]:
        for idx, obj in enumerate(raw.get(category, []), start=1):
            class_name = ""
            try:
                class_name = obj.GetClassName()
            except Exception:
                class_name = obj.__class__.__name__

            if category == "Lines":
                connection = f"{_cubicle_terminal_name(getattr(obj, 'bus1', None))} → {_cubicle_terminal_name(getattr(obj, 'bus2', None))}"
            elif category == "Transformers":
                connection = f"{_cubicle_terminal_name(getattr(obj, 'bushv', None))} → {_cubicle_terminal_name(getattr(obj, 'buslv', None))}"
            else:
                connection = _cubicle_terminal_name(getattr(obj, "bus1", None))

            p_mw, q_mvar = _read_p_q(obj, category)
            loading = safe_float(_get_attribute_first(obj, ["c:loading", "m:loading", "loading"]))

            rows.append({
                "category": category,
                "index": idx,
                "name": str(getattr(obj, "loc_name", "")),
                "class": class_name,
                "connection": connection,
                "status": _element_status(obj),
                "p_mw": p_mw,
                "q_mvar": q_mvar,
                "loading_pct": loading,
                "full_name": object_full_name(obj),
            })

    summary = {
        "Lines": len(raw.get("Lines", [])),
        "Loads": len(raw.get("Loads", [])),
        "Synchronous Generators": len(raw.get("Synchronous Generators", [])),
        "Other Sources": len(raw.get("Other Sources", [])),
        "Transformers": len(raw.get("Transformers", [])),
    }

    return {"summary": summary, "rows": rows}

