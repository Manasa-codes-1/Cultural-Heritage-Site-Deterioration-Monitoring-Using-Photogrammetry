import React, { useState } from 'react';
import { Navbar } from './components/layout/Navbar';
import { Sidebar } from './components/layout/Sidebar';
import type { NavTab } from './components/layout/Sidebar';
import { OverviewPage } from './pages/OverviewPage';
import { SitesPage } from './pages/SitesPage';
import { SurveysPage } from './pages/SurveysPage';
import { SurveyDetailPage } from './pages/SurveyDetailPage';
import { ImageQualityPage } from './pages/ImageQualityPage';
import { PhotogrammetryPage } from './pages/PhotogrammetryPage';
import { MaterialClassificationPage } from './pages/MaterialClassificationPage';
import { DeteriorationDetectionPage } from './pages/DeteriorationDetectionPage';
import { DamageMappingPage } from './pages/DamageMappingPage';
import { TemporalMonitoringPage } from './pages/TemporalMonitoringPage';
import { IntegratedDemoPage } from './pages/IntegratedDemoPage';
import { MonitoringPage } from './pages/MonitoringPage';
import type { MonitoringTab } from './pages/MonitoringPage';
import { ReportsPage } from './pages/ReportsPage';
import { PipelinePlaceholderPage } from './pages/PipelinePlaceholderPage';



export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<NavTab>('overview');
  const [selectedSiteId, setSelectedSiteId] = useState<string | undefined>(undefined);
  const [selectedSurveyId, setSelectedSurveyId] = useState<string | undefined>(undefined);
  const [monitoringTab, setMonitoringTab] = useState<MonitoringTab>('3d-model');

  const handleNavigate = (
    tab: NavTab,
    surveyId?: string,
    siteId?: string,
    subTab?: MonitoringTab
  ) => {
    setCurrentTab(tab);
    if (surveyId) {
      setSelectedSurveyId(surveyId);
    }
    if (siteId) {
      setSelectedSiteId(siteId);
    }
    if (subTab) {
      setMonitoringTab(subTab);
    }
  };

  const handleSelectSiteFromSitesPage = (siteId: string) => {
    setSelectedSiteId(siteId);
    setSelectedSurveyId(undefined);
    setCurrentTab('surveys');
  };

  const handleSelectSurvey = (surveyId: string) => {
    setSelectedSurveyId(surveyId);
  };

  const renderContent = () => {
    switch (currentTab) {
      case 'overview':
        return <OverviewPage onNavigate={handleNavigate} />;

      case 'monitoring':
        return (
          <MonitoringPage
            initialSiteId={selectedSiteId}
            initialSurveyId={selectedSurveyId}
            initialTab={monitoringTab}
            onNavigateToReports={() => setCurrentTab('reports')}
          />
        );

      case 'reports':
        return <ReportsPage onNavigateToMonitoring={() => setCurrentTab('monitoring')} />;

      case 'integrated-demo':
        return <IntegratedDemoPage onNavigateToSurveys={() => setCurrentTab('surveys')} />;

      case 'sites':
        return <SitesPage onSelectSite={handleSelectSiteFromSitesPage} />;

      case 'surveys':
        if (selectedSurveyId) {
          return (
            <SurveyDetailPage
              surveyId={selectedSurveyId}
              onBack={() => setSelectedSurveyId(undefined)}
              onNavigateToQuality={(srvId) => {
                setSelectedSurveyId(srvId);
                setCurrentTab('quality');
              }}
              onNavigateToReconstruction={(srvId) => {
                setSelectedSurveyId(srvId);
                setCurrentTab('viewer');
              }}
            />
          );
        }
        return (
          <SurveysPage
            initialSiteId={selectedSiteId}
            onSelectSurvey={handleSelectSurvey}
          />
        );

      case 'quality':
        return (
          <ImageQualityPage
            initialSurveyId={selectedSurveyId}
            onSelectSurvey={(srvId) => {
              setSelectedSurveyId(srvId);
              setCurrentTab('surveys');
            }}
          />
        );

      case 'viewer':
        return (
          <PhotogrammetryPage
            initialSurveyId={selectedSurveyId}
            onNavigateToQuality={(srvId) => {
              setSelectedSurveyId(srvId);
              setCurrentTab('quality');
            }}
          />
        );

      case 'materials':
        return (
          <MaterialClassificationPage
            initialSurveyId={selectedSurveyId}
            onNavigateToSurveys={() => setCurrentTab('surveys')}
          />
        );

      case 'deterioration':
        return (
          <DeteriorationDetectionPage
            initialSurveyId={selectedSurveyId}
            onNavigateToSurveys={() => setCurrentTab('surveys')}
          />
        );

      case 'damage-mapping':
        return (
          <DamageMappingPage
            initialSurveyId={selectedSurveyId}
            onNavigateToSurveys={() => setCurrentTab('surveys')}
          />
        );

      case 'temporal':
        return (
          <TemporalMonitoringPage
            initialSiteId={selectedSiteId}
            onNavigateToSurveys={() => setCurrentTab('surveys')}
          />
        );



      default:
        return (
          <PipelinePlaceholderPage
            tab={currentTab}
            onNavigateToSurveys={() => setCurrentTab('surveys')}
          />
        );
    }
  };

  return (
    <div className="app-layout">
      <Navbar />
      <div className="app-body">
        <Sidebar
          currentTab={currentTab}
          onSelectTab={(tab) => {
            setCurrentTab(tab);
          }}
        />
        <main className="app-main-content">{renderContent()}</main>
      </div>
    </div>
  );
};

export default App;
