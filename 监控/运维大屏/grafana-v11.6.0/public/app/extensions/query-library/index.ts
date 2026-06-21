import { addEnterpriseProviders } from 'app/AppWrapper';

import { QueryLibraryContextProvider } from './QueryLibraryContextProvider';

export function initQueryLibrary() {
  addEnterpriseProviders(QueryLibraryContextProvider);
}
