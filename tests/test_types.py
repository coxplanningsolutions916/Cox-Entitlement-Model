"""Development types: the taxonomy loads, a project must name one, and the screen is judged against it."""
import pytest

from engine import rules, types
from engine.model import Canon, ModelError, Project


def test_taxonomy_loads_with_the_two_seed_types():
    c = Canon.load()
    assert {"greenfield", "infill", "redevelopment", "rural_resource", "public_infrastructure"} <= set(c.types)
    g, i = c.types["greenfield"], c.types["infill"]
    assert g.primary_issues[0]["id"] == "aquatic" and i.primary_issues[0]["id"] == "compatibility"
    assert "EIR" in g.ceqa_expectation and "Class 32" in i.ceqa_expectation


def test_projects_carry_their_type():
    assert Project.load("riego-rd").development_type.id == "greenfield"
    assert Project.load("lemon-hill").development_type.id == "infill"


def test_a_project_without_a_type_is_refused(tmp_path):
    import shutil, os
    src = os.path.join(os.path.dirname(__file__), "..", "projects", "riego-rd")
    dst = tmp_path / "riego-rd"
    shutil.copytree(src, dst)
    txt = (dst / "project.yaml").read_text().replace("development_type: greenfield", "")
    (dst / "project.yaml").write_text(txt)
    with pytest.raises(ModelError):
        Project.load("riego-rd", root=str(tmp_path))


def test_coverage_names_what_the_screen_misses():
    from engine.report import load_screen
    p = Project.load("lemon-hill")
    cov = types.coverage(p, load_screen(p))
    assert "historic" in {i["id"] for i in cov["missing"]}
    assert {"compatibility", "density_parking", "levers", "utilities", "site_history", "trees", "flood", "traffic", "ceqa"} <= {i["id"] for i in cov["covered"]}
    v = rules.r19_type_coverage(p)
    assert v and not any(x.hard for x in v)
    r = Project.load("riego-rd")
    assert types.coverage(r, load_screen(r))["missing"] == []


def test_greenfield_and_infill_profiles_differ_where_chris_said():
    g = types.profile(Project.load("riego-rd")); i = types.profile(Project.load("lemon-hill"))
    assert "Aquatic" in g["drives"] and "Neighbors" in i["drives"]
    assert "habitat" in " ".join(g["fee_families"]) and "inclusionary" in i["fee_families"]
