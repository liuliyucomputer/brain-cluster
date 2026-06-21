import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { PluginSignatureStatus } from '@grafana/data';
import { config } from '@grafana/runtime';
import { CatalogPlugin } from 'app/features/plugins/admin/types';
import { shouldLoadPluginInFrontendSandbox } from 'app/features/plugins/sandbox/sandbox_plugin_loader_registry';

import { FrontendSandboxSwitch, FrontendSandboxSwitchWrapper } from './FrontendSandboxSwitch';
import { useCreateOrUpdateSandboxSettings, useIsSandboxEligible, useSandboxSettings } from './hooks';

jest.mock('./hooks', () => ({
  useSandboxSettings: jest.fn(),
  useCreateOrUpdateSandboxSettings: jest.fn(),
  useIsSandboxEligible: jest.fn(),
}));

jest.mock('app/features/plugins/sandbox/sandbox_plugin_loader_registry', () => ({
  shouldLoadPluginInFrontendSandbox: jest.fn()
}))

jest.mock('@grafana/runtime', () => ({
  config: {
    featureToggles: {
      pluginsFrontendSandbox: true
    }
  },
  reportInteraction: jest.fn()
}));

const mockPlugin: CatalogPlugin = {
  description: 'The test plugin',
  downloads: 5,
  id: 'test-plugin',
  info: {
    logos: {
      small: 'https://grafana.com/api/plugins/test-plugin/versions/0.0.10/logos/small',
      large: 'https://grafana.com/api/plugins/test-plugin/versions/0.0.10/logos/large',
    },
    keywords: ['test', 'plugin'],
  },
  name: 'Test Plugin',
  orgName: 'Test',
  popularity: 0,
  signature: PluginSignatureStatus.valid,
  publishedAt: '2020-09-01',
  updatedAt: '2021-06-28',
  hasUpdate: false,
  isInstalled: false,
  isCore: false,
  isDev: false,
  isEnterprise: false,
  isDisabled: false,
  isDeprecated: false,
  isPublished: true,
  isManaged: false,
  isPreinstalled: { found: false, withVersion: false },
};

const useSandboxSettingsMock = useSandboxSettings as jest.Mock;
const useCreateOrUpdateSandboxSettingsMock = useCreateOrUpdateSandboxSettings as jest.Mock;
const useIsSandboxEligibleMock = useIsSandboxEligible as jest.Mock;
const shouldLoadPluginInFrontendSandboxMock = shouldLoadPluginInFrontendSandbox as jest.Mock;

describe('FrontendSandboxSwitch', () => {
  const original = window.location;
  beforeEach(() => {
    config.enableFrontendSandboxForPlugins = [];
    useSandboxSettingsMock.mockReturnValue([null, false]);
    useCreateOrUpdateSandboxSettingsMock.mockReturnValue([jest.fn(), { isLoading: false }]);
    shouldLoadPluginInFrontendSandboxMock.mockResolvedValue(false);

    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { reload: jest.fn(), search: '' },
    });

  });

  afterEach(() => {
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: original,
    });
  })

  it('renders switch when settings are loaded', () => {
    useSandboxSettingsMock.mockReturnValue([{ enabled: false }, false]);
    render(<FrontendSandboxSwitch plugin={mockPlugin} />);
    expect(screen.getByRole('switch')).toBeInTheDocument();
    expect(screen.getByRole('switch')).not.toBeChecked();
  });


  it('updates state when switch is toggled', async () => {
    const mockSubmit = jest.fn();
    useCreateOrUpdateSandboxSettingsMock.mockReturnValue([mockSubmit, { isLoading: false }]);

    render(<FrontendSandboxSwitch plugin={mockPlugin} />);
    await userEvent.click(screen.getByRole('switch'));

    expect(mockSubmit).toHaveBeenCalledWith({
      plugin: 'test-plugin',
      enabled: true,
      apiAllowList: [],
    });

    expect(window.location.reload).toHaveBeenCalled();
  });

  it('reloads the page after a succesful update', async () => {
    const mockSubmit = jest.fn();

    useCreateOrUpdateSandboxSettingsMock
      .mockReturnValueOnce([mockSubmit, { isLoading: false }])
      .mockReturnValueOnce([jest.fn(), { isLoading: true, data: { spec: { enabled: true } } }])
      .mockReturnValueOnce([jest.fn(), { isLoading: false }]);

    render(<FrontendSandboxSwitch plugin={mockPlugin} />);

    expect(screen.queryByText('Browser reload required')).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('switch'));

    expect(mockSubmit).toHaveBeenCalledWith({
      plugin: 'test-plugin',
      enabled: true,
      apiAllowList: [],
    });

    expect(window.location.reload).toHaveBeenCalled();
  });

});

describe('It overwrites the default oss valuie', () => {
  beforeEach(() => {
    config.enableFrontendSandboxForPlugins = [];
    useSandboxSettingsMock.mockReturnValue([null, false]);
    useCreateOrUpdateSandboxSettingsMock.mockReturnValue([jest.fn(), { isLoading: false }]);
  });

  it('Should default to enabled if it is in the config and nothing in the store', async () => {
    shouldLoadPluginInFrontendSandboxMock.mockResolvedValue(true);
    // no stored setting
    useSandboxSettingsMock.mockReturnValue([null, false]);
    render(<FrontendSandboxSwitch plugin={mockPlugin} />);
    expect(screen.getByRole('switch')).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByRole('switch')).toBeChecked();

    })
  });

  it('Should default to the stored value (false) even if it is in enabled by config', async () => {
    config.enableFrontendSandboxForPlugins = ['test-plugin'];
    // stored setting is false (disabled) and configuration file has it enabled
    useSandboxSettingsMock.mockReturnValue([{ enabled: false }, false]);
    render(<FrontendSandboxSwitch plugin={mockPlugin} />);
    expect(screen.getByRole('switch')).toBeInTheDocument();
    expect(screen.getByRole('switch')).not.toBeChecked();
  });

  it('Should default to the stored value (true) even if it is in enabled by config', async () => {
    config.enableFrontendSandboxForPlugins = ['test-plugin'];
    // stored setting is false (disabled) and configuration file has it enabled
    useSandboxSettingsMock.mockReturnValue([{ enabled: true }, false]);
    render(<FrontendSandboxSwitch plugin={mockPlugin} />);
    expect(screen.getByRole('switch')).toBeInTheDocument();
    expect(screen.getByRole('switch')).toBeChecked();
  });
});

describe('FrontendSandboxSwitchWrapper', () => {
  it('renders nothing when plugin is not eligible', () => {
    useIsSandboxEligibleMock.mockReturnValue(false);
    const { container } = render(<FrontendSandboxSwitchWrapper plugin={mockPlugin} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders switch when plugin is eligible', () => {
    useIsSandboxEligibleMock.mockReturnValue(true);
    useSandboxSettingsMock.mockReturnValue([{ enabled: false }, false]);
    render(<FrontendSandboxSwitchWrapper plugin={mockPlugin} />);
    expect(screen.getByRole('switch')).toBeInTheDocument();
  });

  it('renders nothing when plugin is undefined', () => {
    const { container } = render(<FrontendSandboxSwitchWrapper />);
    expect(container).toBeEmptyDOMElement();
  });
});
