/**
 * Route screen: Cohort report.
 *
 * Role-gated in the navigation only; the API is the real boundary.
 */
import { InstitutionDashboard } from '@/features/institution/InstitutionDashboard';
import { AppRoute } from '@/routes/AppRoute';
import { useSession } from '@/services/SessionProvider';

export default function InstitutionScreen() {
  const { session } = useSession();
  return (
    <AppRoute title="Cohort report">
      <InstitutionDashboard token={session.token} />
    </AppRoute>
  );
}
