import { render, fireEvent, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TestProvider } from 'test/helpers/TestProvider';

import { config } from '@grafana/runtime';

import { Theme } from '../types';

import { ReportsSettingsPage } from './ReportsSettingsPage';


beforeEach(() => {
  jest.clearAllMocks();
  window.URL.createObjectURL = jest.fn(() => 'blob:https://');
  config.featureToggles.newPDFRendering = true;
});

afterEach(() => {
  (window.URL.createObjectURL as jest.Mock).mockReset();
});

const mockPost = jest.fn(() => {
  return Promise.resolve([]);
});

const mockUpdate: jest.Mock = jest.fn(() => Promise.resolve([]));
window.fetch = mockUpdate;

jest.mock('@grafana/runtime', () => {
  return {
    ...jest.requireActual('@grafana/runtime'),
    getBackendSrv() {
      return {
        get: (url: string) => {
          return {
            branding: {
              emailFooterLink: 'https://footer-link.com',
              emailFooterMode: 'sent-by',
              emailFooterText: 'Test',
              emailLogoUrl: 'https://email-logo.jpg',
              reportLogoUrl: 'https://report-logo.jpg',
            },
            id: 0,
            orgId: 1,
            userId: 1,
            pdfTheme: Theme.Light,
            embeddedImageTheme: Theme.Dark
          };
        },
        post: mockPost,
      };
    },
    config: {
      ...jest.requireActual('@grafana/runtime').config,
      buildInfo: {
        edition: 'Enterprise',
        version: '9.0.0',
        commit: 'abc123',
        env: 'dev',
        latestVersion: '',
        hasUpdate: false,
        hideVersion: false,
      },
      licenseInfo: {},
      featureToggles: {},
      rendererAvailable: true,
    },
  };
});

jest.mock('app/core/core', () => {
  return {
    contextSrv: {
      hasPermission: () => true,
    },
    appEvents: {
      emit: jest.fn(),
      publish: jest.fn(),
    },
  };
});

const setup = () => {
  render(
    <TestProvider>
      <ReportsSettingsPage />
    </TestProvider>
  );
};

describe('ReportsSettingPage', () => {
  it('should render existing settings', async () => {
    setup();

    expect(await screen.findByText(/attachment settings/i)).toBeInTheDocument();
    const reportLogoUrl= screen.getByTestId('url-field-branding.reportLogoUrl');
    expect(reportLogoUrl).toHaveValue('https://report-logo.jpg');
    const emailLogoUrl= screen.getByTestId('url-field-branding.emailLogoUrl');
    expect(emailLogoUrl).toHaveValue('https://email-logo.jpg');
    expect(screen.getByRole('radio', { name: /sent by/i })).toBeChecked();
    expect(screen.getByRole('textbox', { name: /footer link text/i })).toHaveValue('Test');
    expect(screen.getByRole('textbox', { name: /footer link url/i })).toHaveValue('https://footer-link.com');
    expect(screen.getByText(/The theme will be applied to the PDF attached to the report/i)).toBeInTheDocument();
    expect(screen.getByText(/The theme will be applied to the dashboard image embedded in the email/i)).toBeInTheDocument();
    const lightTheme = screen.getAllByRole('radio', { name: /light/i });
    expect(lightTheme[0]).toBeChecked();
    const darkTheme = screen.getAllByRole('radio', { name: /dark/i });
    expect(darkTheme[1]).toBeChecked();
  });

  it('should hide footer link and text if footer mode is None', async () => {
    setup();
    expect(await screen.findByRole('radio', { name: /sent by/i })).toBeChecked();
    expect(screen.getByRole('textbox', { name: /footer link text/i })).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: /footer link url/i })).toBeInTheDocument();

    const none = screen.getByRole('radio', { name: /none/i });
    fireEvent.click(none);

    expect(await screen.findByRole('radio', { name: /none/i })).toBeChecked();
    expect(screen.queryByRole('textbox', { name: /footer link text/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('textbox', { name: /footer link url/i })).not.toBeInTheDocument();
  });

  it('should update the form fields on change', async () => {
    setup();
    const user = userEvent.setup();
    expect(await screen.findByText(/attachment settings/i)).toBeInTheDocument();
    const reportLogoUrl= screen.getByTestId('url-field-branding.reportLogoUrl');
    expect(reportLogoUrl).toHaveValue('https://report-logo.jpg');
    const emailLogoUrl= screen.getByTestId('url-field-branding.emailLogoUrl');
    expect(emailLogoUrl).toHaveValue('https://email-logo.jpg');
    await user.clear(reportLogoUrl);
    await user.type(reportLogoUrl, 'https://new-logo.png');
    const footerText = screen.getByRole('textbox', { name: /footer link text/i });
    await user.clear(footerText);
    await user.type(footerText, 'New company');
    const themePicker = screen.getAllByRole('radio', { name: /dark/i });
    fireEvent.click(themePicker[0]);
    await user.click(screen.getByRole('button', { name: 'Save' }));

    const testData: FormData = mockUpdate.mock.calls[0][1].body;
    const config = testData.get('config') as string;
    expect(JSON.parse(config)).toEqual({
      id: 0,
      orgId: 1,
      userId: 1,
      pdfTheme: 'dark',
      embeddedImageTheme: 'dark',
      branding:{
      emailFooterLink: 'https://footer-link.com',
      emailFooterMode: 'sent-by',
      emailFooterText: 'New company',
      emailLogoUrl: 'https://email-logo.jpg',
      reportLogoUrl: 'https://new-logo.png',
    }}
  );
  });

  it('should allow uploading files', async () => {
    setup();
    const user = userEvent.setup();
    expect(await screen.findByText(/attachment settings/i)).toBeInTheDocument();
    const reportLogoPicker = screen.getByTestId('resource-picker-branding.reportLogoUrl');
    await user.click(within(reportLogoPicker).getByRole('radio', { name: /upload file/i }));
    await user.upload(
      within(reportLogoPicker).getByTestId('dropzone').querySelector('input[type="file"]')!,
      new File([JSON.stringify({ ping: true })], 'reportLogoCustom.png', { type: 'image/png' })
    );

    const emailLogoPicker = screen.getByTestId('resource-picker-branding.emailLogoUrl');
    await user.click(within(emailLogoPicker).getByRole('radio', { name: /upload file/i }));
    await user.upload(
      within(emailLogoPicker).getByTestId('dropzone').querySelector('input[type="file"]')!,
      new File([JSON.stringify({ ping: true })], 'emailLogoCustom.png', { type: 'image/png' })
    );

    await user.click(screen.getByRole('button', { name: 'Save' }));

    const testData: FormData = mockUpdate.mock.calls[0][1].body;
    const files = testData.getAll('files');
    expect(files).toMatchObject([{ path: './emailLogoCustom.png' }, { path: './reportLogoCustom.png' }]);
  });

  it('should not render PDF theme option when newPDFRendering FF is false', async () => {
    config.featureToggles.newPDFRendering = false;
    setup();
    expect(await screen.findByText(/attachment settings/i)).toBeInTheDocument();
    expect(screen.queryByText(/The theme will be applied to the PDF attached to the report/i)).not.toBeInTheDocument();
  });
});
