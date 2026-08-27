import { LogoutOutlined } from '@ant-design/icons'
import { Button, Layout, Menu, Space, Typography } from 'antd'
import type { MenuProps } from 'antd'
import { useEffect, useMemo, useState } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'

import { APP_MENU, filterMenu } from '../router/menu'
import type { AppMenuItem } from '../router/menu'
import { useAuthStore } from '../store/auth'

const { Header, Sider, Content } = Layout

type AntdMenuItem = Required<MenuProps>['items'][number]

function toAntdItems(menus: AppMenuItem[]): AntdMenuItem[] {
  return menus.map((m) => ({
    key: m.path,
    label: m.label,
    icon: m.icon,
    children: m.children ? toAntdItems(m.children) : undefined,
  }))
}

export default function BasicLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const user = useAuthStore((state) => state.user)
  const permissions = useAuthStore((state) => state.permissions)
  const logout = useAuthStore((state) => state.logout)

  const items = useMemo(() => toAntdItems(filterMenu(APP_MENU, permissions)), [permissions])

  // 依据当前路径展开对应父级子菜单。
  const defaultOpenKeys = useMemo(
    () =>
      APP_MENU.filter((m) => m.children?.some((c) => location.pathname.startsWith(c.path))).map(
        (m) => m.path,
      ),
    [location.pathname],
  )
  const [openKeys, setOpenKeys] = useState<string[]>(defaultOpenKeys)
  useEffect(() => {
    setOpenKeys(defaultOpenKeys)
  }, [defaultOpenKeys])

  const handleMenuClick: MenuProps['onClick'] = ({ key }) => navigate(key)
  const handleLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider collapsible collapsed={collapsed} onCollapse={setCollapsed}>
        <div
          style={{
            height: 48,
            margin: 16,
            color: '#fff',
            textAlign: 'center',
            lineHeight: '48px',
            fontSize: 18,
            fontWeight: 600,
            whiteSpace: 'nowrap',
          }}
        >
          KBMS
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          openKeys={openKeys}
          onOpenChange={setOpenKeys}
          items={items}
          onClick={handleMenuClick}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            background: '#fff',
            padding: '0 16px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <Typography.Text strong>知识库管理平台</Typography.Text>
          <Space>
            <Typography.Text>{user?.display_name ?? user?.username}</Typography.Text>
            <Button type="text" icon={<LogoutOutlined />} onClick={handleLogout}>
              退出
            </Button>
          </Space>
        </Header>
        <Content style={{ margin: 16 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}