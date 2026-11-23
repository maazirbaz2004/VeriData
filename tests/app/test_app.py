"""Unit and integration tests for the VeriData Streamlit application (Phase 7 Section 6)."""

import sys
from pathlib import Path
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.make_noise_csv import generate_noise_dataset
from veridata.agent.session import create_session
from veridata.app.compat import st
from veridata.app.components import (
    render_facts_viewer,
    render_findings,
    render_naive_vs_validated,
    render_overview,
    render_rejected,
    render_report_export,
    render_settings,
)
from veridata.app.main import main
from veridata.app.session import get_current_session, initialize_session, reset_session
from veridata.config import PipelineConfig


@pytest.fixture
def mock_session(tmp_path):
    df = pd.DataFrame({
        "age": [20, 25, 30, 35, 40, 45, 50, 55],
        "charges": [1000.0, 1200.0, 1500.0, 2000.0, 3000.0, 4000.0, 5000.0, 6000.0],
        "smoker": ["no", "no", "no", "yes", "no", "yes", "no", "yes"],
    })
    cfg = PipelineConfig(name="test_app_dataset")
    sess = create_session(df, cfg, out_dir=tmp_path)
    # Populate a finding
    sess.ask("Compare charges by smoker")
    return sess


def test_app_main_runs_without_exceptions():
    """Ensure the main entrypoint executes without error under the headless shim."""
    main()


def test_settings_rendering():
    settings = render_settings()
    assert "alpha" in settings
    assert "correction" in settings
    assert "effect_floor" in settings
    assert settings["alpha"] == 0.05
    assert settings["correction"] == "bh"


def test_session_initialization_and_reset(tmp_path):
    df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    sess = initialize_session(df, dataset_name="custom")
    assert sess is not None
    assert get_current_session() is not None

    reset_session()
    assert get_current_session() is None


def test_tab_components_render(mock_session):
    sess = mock_session
    # All 7 tab renderers must execute without throwing errors
    render_overview(sess)
    render_findings(sess)
    render_rejected(sess)
    render_naive_vs_validated(sess)
    render_facts_viewer(sess)
    render_report_export(sess)


def test_noise_generator_properties():
    df_noise = generate_noise_dataset(n_rows=200, seed=42)
    assert df_noise.shape == (200, 25)
    # Ensure all expected columns are present
    assert any(c.startswith("num_norm_") for c in df_noise.columns)
    assert any(c.startswith("bin_") for c in df_noise.columns)
    assert any(c.startswith("cat_") for c in df_noise.columns)


def test_demo_datasets_exist():
    demo_dir = Path("data/demo")
    assert (demo_dir / "insurance.csv").exists()
    assert (demo_dir / "pure_noise.csv").exists()
    assert (demo_dir / "messy.csv").exists()
    assert (demo_dir / "telco_churn.csv").exists()
