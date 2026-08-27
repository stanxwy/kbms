"""permission_engine 数据权限引擎单元测试。

覆盖：四维实体（global/department/role/user）OR 判定、部门祖先链继承、
停用用户全拒、无权限单元拒绝，以及 _is_authorized 纯函数。
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from admin.models.knowledge import KnowledgeUnit, UnitPermission
from admin.models.org import Department
from admin.models.user import User, UserRole
from admin.services import permission_engine


async def _seed_departments(session: AsyncSession) -> None:
    session.add_all(
        [
            Department(id=10, name="总公司", parent_id=None),
            Department(id=11, name="研发部", parent_id=10),
            Department(id=12, name="研发一组", parent_id=11),
            Department(id=20, name="营销部", parent_id=10),
        ]
    )
    await session.flush()


async def _seed_user(session: AsyncSession, *, status: int = 1, department_id: int | None = 12) -> int:
    user = User(
        id=1, username="alice", password_hash="x", display_name="Alice", status=status, department_id=department_id
    )
    session.add(user)
    await session.flush()
    return user.id


async def _seed_unit(session: AsyncSession, source: str = "alpha") -> int:
    unit = KnowledgeUnit(id=1, unit_code=f"KU-{source}", title=source, source_file_name=source, file_type="pdf")
    session.add(unit)
    await session.flush()
    return unit.id


async def test_global_authorizes(authz_session):
    session = authz_session
    uid = await _seed_user(session)
    await _seed_departments(session)
    unit_id = await _seed_unit(session)
    session.add(UnitPermission(unit_id=unit_id, target_type="global", target_id=0))
    await session.flush()

    result = await permission_engine.check_permissions(session, uid, [unit_id])
    assert result.authorized_unit_ids == [unit_id]
    assert result.unauthorized_unit_ids == []


async def test_department_ancestor_authorizes(authz_session):
    session = authz_session
    uid = await _seed_user(session, department_id=12)  # 研发一组 -> 研发部 -> 总公司
    await _seed_departments(session)
    unit_id = await _seed_unit(session)
    # 目标为祖先「研发部」(11)，用户部门 12 的祖先链含 11。
    session.add(UnitPermission(unit_id=unit_id, target_type="department", target_id=11))
    await session.flush()

    result = await permission_engine.check_permissions(session, uid, [unit_id])
    assert result.authorized_unit_ids == [unit_id]


async def test_root_department_inherited(authz_session):
    session = authz_session
    uid = await _seed_user(session, department_id=12)
    await _seed_departments(session)
    unit_id = await _seed_unit(session)
    # 目标为根「总公司」(10)，最深子部门用户也应继承。
    session.add(UnitPermission(unit_id=unit_id, target_type="department", target_id=10))
    await session.flush()

    result = await permission_engine.check_permissions(session, uid, [unit_id])
    assert result.authorized_unit_ids == [unit_id]


async def test_department_non_ancestor_denies(authz_session):
    session = authz_session
    uid = await _seed_user(session, department_id=12)
    await _seed_departments(session)
    unit_id = await _seed_unit(session)
    # 目标「营销部」(20) 不在用户部门 12 的祖先链中。
    session.add(UnitPermission(unit_id=unit_id, target_type="department", target_id=20))
    await session.flush()

    result = await permission_engine.check_permissions(session, uid, [unit_id])
    assert result.authorized_unit_ids == []
    assert result.unauthorized_unit_ids == [unit_id]


async def test_role_authorizes(authz_session):
    session = authz_session
    uid = await _seed_user(session)
    await _seed_departments(session)
    unit_id = await _seed_unit(session)
    session.add(UserRole(id=1, user_id=uid, role_id=100))
    await session.flush()
    session.add(UnitPermission(unit_id=unit_id, target_type="role", target_id=100))
    await session.flush()

    result = await permission_engine.check_permissions(session, uid, [unit_id])
    assert result.authorized_unit_ids == [unit_id]


async def test_role_mismatch_denies(authz_session):
    session = authz_session
    uid = await _seed_user(session)
    await _seed_departments(session)
    unit_id = await _seed_unit(session)
    session.add(UserRole(id=1, user_id=uid, role_id=100))
    await session.flush()
    session.add(UnitPermission(unit_id=unit_id, target_type="role", target_id=999))
    await session.flush()

    result = await permission_engine.check_permissions(session, uid, [unit_id])
    assert result.unauthorized_unit_ids == [unit_id]


async def test_user_authorizes(authz_session):
    session = authz_session
    uid = await _seed_user(session)
    await _seed_departments(session)
    unit_id = await _seed_unit(session)
    session.add(UnitPermission(unit_id=unit_id, target_type="user", target_id=uid))
    await session.flush()

    result = await permission_engine.check_permissions(session, uid, [unit_id])
    assert result.authorized_unit_ids == [unit_id]


async def test_disabled_user_denies_all(authz_session):
    session = authz_session
    uid = await _seed_user(session, status=0)
    await _seed_departments(session)
    unit_id = await _seed_unit(session)
    session.add(UnitPermission(unit_id=unit_id, target_type="global", target_id=0))
    await session.flush()

    result = await permission_engine.check_permissions(session, uid, [unit_id])
    assert result.authorized_unit_ids == []
    assert result.unauthorized_unit_ids == [unit_id]


async def test_unit_without_permissions_denies(authz_session):
    session = authz_session
    uid = await _seed_user(session)
    await _seed_departments(session)
    unit_id = await _seed_unit(session)

    result = await permission_engine.check_permissions(session, uid, [unit_id])
    assert result.authorized_unit_ids == []
    assert result.unauthorized_unit_ids == [unit_id]


async def test_empty_unit_ids(authz_session):
    session = authz_session
    result = await permission_engine.check_permissions(session, 1, [])
    assert result.authorized_unit_ids == []
    assert result.unauthorized_unit_ids == []


def test_is_authorized_or_logic():
    assert permission_engine._is_authorized(
        [UnitPermission(unit_id=1, target_type="global", target_id=0)],
        user_id=5,
        role_ids=set(),
        ancestor_ids=set(),
    )
    assert permission_engine._is_authorized(
        [UnitPermission(unit_id=1, target_type="department", target_id=3)],
        user_id=5,
        role_ids=set(),
        ancestor_ids={1, 2, 3},
    )
    assert permission_engine._is_authorized(
        [UnitPermission(unit_id=1, target_type="role", target_id=9)],
        user_id=5,
        role_ids={9},
        ancestor_ids=set(),
    )
    assert permission_engine._is_authorized(
        [UnitPermission(unit_id=1, target_type="user", target_id=5)],
        user_id=5,
        role_ids=set(),
        ancestor_ids=set(),
    )
    assert not permission_engine._is_authorized(
        [UnitPermission(unit_id=1, target_type="user", target_id=6)],
        user_id=5,
        role_ids=set(),
        ancestor_ids=set(),
    )
    assert not permission_engine._is_authorized([], user_id=5, role_ids=set(), ancestor_ids=set())
