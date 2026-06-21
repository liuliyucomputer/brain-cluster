import { of } from 'rxjs';

import { PluginMeta, PluginSignatureType } from '@grafana/data';
import { BackendSrvRequest, config, FetchError, FetchResponse } from '@grafana/runtime';
import { BackendSrv } from 'app/core/services/backend_srv';
import { getPluginSettings } from 'app/features/plugins/pluginSettings';
import {
  shouldLoadPluginInFrontendSandbox,
  isPluginFrontendSandboxEnabled,
} from 'app/features/plugins/sandbox/sandbox_plugin_loader_registry';

import { initSandboxPluginLoaderRegistry } from './sandboxLoader';

const request = jest.fn<Promise<FetchResponse | FetchError>, BackendSrvRequest[]>();

const backendSrv = {
  fetch: (options: BackendSrvRequest) => {
    return of(request(options));
  },
} as unknown as BackendSrv;

jest.mock('@grafana/runtime', () => ({
  ...jest.requireActual('@grafana/runtime'),
  getBackendSrv: () => backendSrv,
}));

jest.mock('app/features/plugins/pluginSettings', () => ({
  getPluginSettings: jest.fn(),
}));

jest.mock('app/features/plugins/sandbox/sandbox_plugin_loader_registry', () => ({
  ...jest.requireActual('app/features/plugins/sandbox/sandbox_plugin_loader_registry'),
  isPluginFrontendSandboxEnabled: jest.fn(),
}));

const getPluginSettingsMock = getPluginSettings as jest.MockedFunction<typeof getPluginSettings>;
const fakePlugin: PluginMeta = {
  id: 'test-plugin',
  name: 'Test Plugin',
} as PluginMeta;

const isPluginFrontendSandboxEnabledInOssMock = isPluginFrontendSandboxEnabled as jest.MockedFunction<
  typeof isPluginFrontendSandboxEnabled
>;

describe('shouldLoadPluginInFrontendSandbox', () => {
  const originalNodeEnv = process.env.NODE_ENV;
  const plugin = 'test-plugin';

  beforeEach(() => {
    config.featureToggles.pluginsFrontendSandbox = true;
    config.bootData.user.isSignedIn = true;
    process.env.NODE_ENV = 'development';
    getPluginSettingsMock.mockResolvedValue({ ...fakePlugin, signatureType: PluginSignatureType.community });
    initSandboxPluginLoaderRegistry();
    request.mockReset();
  });

  afterAll(() => {
    process.env.NODE_ENV = originalNodeEnv;
  });

  it('should be enabled for a configured plugin', async () => {
    request.mockReturnValue(
      Promise.resolve({ data: { items: [{ spec: { enabled: true, plugin } }] } } as FetchResponse)
    );
    const res = await shouldLoadPluginInFrontendSandbox({ pluginId: plugin });
    expect(res).toBe(true);
  });

  it('should use the cache for further requests', async () => {
    request.mockReturnValueOnce(
      Promise.resolve({ data: { items: [{ spec: { enabled: true, plugin } }] } } as FetchResponse)
    );
    const res = await shouldLoadPluginInFrontendSandbox({ pluginId: plugin });
    expect(res).toBe(true);
    const resBis = await shouldLoadPluginInFrontendSandbox({ pluginId: plugin });
    expect(resBis).toBe(true);
    expect(request).toHaveBeenCalledTimes(1);
  });

  it('should be disabled if the request returns a 404', async () => {
    request.mockReturnValue(Promise.reject({ status: 404 } as FetchError));
    // OSS fallback method returns false
    isPluginFrontendSandboxEnabledInOssMock.mockResolvedValue(false);
    const res = await shouldLoadPluginInFrontendSandbox({ pluginId: plugin });
    expect(res).toBe(false);
  });

  it('should be disabled if the request returns a 403', async () => {
    request.mockReturnValue(Promise.reject({ status: 403 } as FetchError));
    // OSS fallback method returns false
    isPluginFrontendSandboxEnabledInOssMock.mockResolvedValue(false);
    const res = await shouldLoadPluginInFrontendSandbox({ pluginId: plugin });
    expect(res).toBe(false);
  });

  it('should be disabled if the request returns an empty list', async () => {
    request.mockReturnValue(Promise.resolve({ data: {} } as FetchResponse));
    const res = await shouldLoadPluginInFrontendSandbox({ pluginId: plugin });
    expect(res).toBe(false);
  });

  it('should fallback to the OSS check if the request returns a 404', async () => {
    request.mockReturnValue(Promise.reject({ status: 404 } as FetchError));
    // OSS fallback method returns true
    isPluginFrontendSandboxEnabledInOssMock.mockResolvedValue(true);
    const res = await shouldLoadPluginInFrontendSandbox({ pluginId: plugin });
    expect(res).toBe(true);
  });

  it('should fallback to the OSS check if the user is not logged in', async () => {
    config.bootData.user.isSignedIn = false;
    // OSS fallback method returns true
    isPluginFrontendSandboxEnabledInOssMock.mockResolvedValue(true);
    const res = await shouldLoadPluginInFrontendSandbox({ pluginId: plugin });
    expect(res).toBe(true);
  });
});
