import pytest

from hackathon_worker.domain.exceptions import InvalidStateTransitionError
from hackathon_worker.domain.fsm import JobStateMachine, WorkerJobPhase


def test_fsm_happy_path():
    f = JobStateMachine()
    assert f.phase == WorkerJobPhase.PENDING
    f.start_processing()
    assert f.phase == WorkerJobPhase.PROCESSING
    f.complete()
    assert f.phase == WorkerJobPhase.COMPLETED


def test_fsm_double_start():
    f = JobStateMachine()
    f.start_processing()
    with pytest.raises(InvalidStateTransitionError):
        f.start_processing()


def test_fsm_fail_from_pending():
    f = JobStateMachine()
    f.fail()
    assert f.phase == WorkerJobPhase.FAILED


def test_fsm_fail_from_processing():
    f = JobStateMachine()
    f.start_processing()
    f.fail()
    assert f.phase == WorkerJobPhase.FAILED


def test_fsm_fail_after_complete_raises():
    f = JobStateMachine()
    f.start_processing()
    f.complete()
    with pytest.raises(InvalidStateTransitionError):
        f.fail()
