import { ResourceForCreate } from 'app/features/apiserver/types';

export interface RequestArg {
  /** Name of the SandboxSettings */
  name: string;
  showErrorAlert?: boolean;
}

export interface UpdateRequestArg<T> extends RequestArg {
  /** SandboxSettingsSpec */
  body: ResourceForCreate<Partial<T>>;
}

export type SandboxSettingsSpec = {
  /** Target plugin */
  plugin: string;
  /** Should the sandbox be enabled */
  enabled: boolean;
  // List of APIs allowed while sandboxed (e.g. window). Unused for now
  apiAllowList?: string[];
};
