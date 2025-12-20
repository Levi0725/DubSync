"""
DubSync Test Fixtures

Közös teszt fixtures és segédfüggvények.
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from dubsync.models.database import Database, init_database
from dubsync.models.project import Project
from dubsync.models.cue import Cue
from dubsync.utils.constants import CueStatus


@pytest.fixture
def temp_dir():
    """
    Ideiglenes könyvtár tesztekhez.
    """
    dir_path = Path(tempfile.mkdtemp())
    yield dir_path
    shutil.rmtree(dir_path, ignore_errors=True)


@pytest.fixture
def memory_db():
    """
    Memória-alapú adatbázis tesztekhez.
    """
    db = Database(None)  # Memory database
    init_database(db)
    yield db
    db.close()


@pytest.fixture
def file_db(temp_dir):
    """
    Fájl-alapú adatbázis tesztekhez.
    """
    db_path = temp_dir / "test_project.dubsync"
    db = Database(db_path)
    init_database(db)
    yield db
    db.close()


@pytest.fixture
def sample_project(memory_db):
    """
    Minta projekt tesztekhez.
    """
    project = Project.load(memory_db, 1)
    assert project is not None, "Project with id 1 should exist"
    project.title = "Teszt Epizód"
    project.series_title = "Teszt Sorozat"
    project.season = "1"
    project.episode = "5"
    project.translator = "Teszt Fordító"
    project.editor = "Teszt Lektor"
    project.save(memory_db)
    return project


@pytest.fixture
def sample_cues(memory_db, sample_project):
    """
    Minta cue-k tesztekhez.
    """
    cues = [
        Cue(
            project_id=sample_project.id,
            cue_index=1,
            time_in_ms=0,
            time_out_ms=2000,
            source_text="Hello, how are you?",
            translated_text="Szia, hogy vagy?",
            character_name="ANNA",
            status=CueStatus.TRANSLATED,
        ),
        Cue(
            project_id=sample_project.id,
            cue_index=2,
            time_in_ms=2500,
            time_out_ms=5000,
            source_text="I'm fine, thank you.",
            translated_text="Jól vagyok, köszönöm.",
            character_name="PETER",
            status=CueStatus.APPROVED,
        ),
        Cue(
            project_id=sample_project.id,
            cue_index=3,
            time_in_ms=5500,
            time_out_ms=8000,
            source_text="What are you doing today?",
            translated_text="",  # Untranslated
            character_name="ANNA",
            status=CueStatus.NEW,
        ),
    ]
    
    for cue in cues:
        cue.save(memory_db)
    
    return cues


@pytest.fixture
def sample_srt_content():
    """
    Minta SRT tartalom tesztekhez.
    """
    return """1
00:00:00,000 --> 00:00:02,000
Hello, how are you?

2
00:00:02,500 --> 00:00:05,000
I'm fine, thank you.

3
00:00:05,500 --> 00:00:08,000
What are you doing today?

4
00:00:08,500 --> 00:00:12,000
I'm going to the store.
Do you want to come?
"""


@pytest.fixture
def sample_srt_file(temp_dir, sample_srt_content):
    """
    Minta SRT fájl tesztekhez.
    """
    srt_path = temp_dir / "test.srt"
    srt_path.write_text(sample_srt_content, encoding="utf-8")
    return srt_path
