// Example React component for LinkedIn connection management
import React, { useState, useEffect } from 'react';
import { Button, Card, Alert, Badge } from 'your-ui-library';
import { api } from '@/lib/api';

interface LinkedInConnection {
  id: string;
  account_status: string;
  display_name: string;
  profile_url: string;
  created_at: string;
}

export function LinkedInConnectionManager({ companyId }: { companyId: string }) {
  const [connections, setConnections] = useState<LinkedInConnection[]>([]);
  const [loading, setLoading] = useState(false);
  const [connecting, setConnecting] = useState(false);

  useEffect(() => {
    fetchConnections();
  }, [companyId]);

  const fetchConnections = async () => {
    setLoading(true);
    try {
      const response = await api.get(`/api/v1/linkedin/connections?company_id=${companyId}`);
      setConnections(response.data);
    } catch (error) {
      console.error('Failed to fetch LinkedIn connections:', error);
    } finally {
      setLoading(false);
    }
  };

  const connectLinkedIn = async () => {
    setConnecting(true);
    try {
      const response = await api.post('/api/v1/linkedin/connect', { company_id: companyId });
      window.location.href = response.data.auth_url;
    } catch (error) {
      console.error('Failed to create LinkedIn connection:', error);
      setConnecting(false);
    }
  };

  const reconnectAccount = async (connectionId: string) => {
    try {
      const response = await api.post(`/api/v1/linkedin/reconnect/${connectionId}`);
      window.location.href = response.data.auth_url;
    } catch (error) {
      console.error('Failed to reconnect:', error);
    }
  };

  const getStatusBadge = (status: string) => {
    const statusConfig = {
      OK: { color: 'green', text: 'Connected' },
      CREDENTIALS: { color: 'red', text: 'Reconnect Required' },
      CONNECTING: { color: 'yellow', text: 'Connecting...' },
      ERROR: { color: 'red', text: 'Error' }
    };

    const config = statusConfig[status] || { color: 'gray', text: status };
    return <Badge color={config.color}>{config.text}</Badge>;
  };

  if (loading) return <div>Loading...</div>;

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">LinkedIn Connections</h3>
        {connections.length === 0 && (
          <Button onClick={connectLinkedIn} loading={connecting}>
            Connect LinkedIn Account
          </Button>
        )}
      </div>

      {connections.length === 0 && !connecting && (
        <Alert>
          Connect your LinkedIn account to start sending personalized messages to leads.
        </Alert>
      )}

      {connections.map((connection) => (
        <Card key={connection.id} className="p-4">
          <div className="flex justify-between items-start">
            <div>
              <h4 className="font-medium">{connection.display_name}</h4>
              <a 
                href={connection.profile_url} 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-sm text-blue-600 hover:underline"
              >
                View Profile
              </a>
              <p className="text-sm text-gray-500 mt-1">
                Connected: {new Date(connection.created_at).toLocaleDateString()}
              </p>
            </div>
            <div className="flex items-center gap-2">
              {getStatusBadge(connection.account_status)}
              {connection.account_status === 'CREDENTIALS' && (
                <Button 
                  size="sm" 
                  variant="outline"
                  onClick={() => reconnectAccount(connection.id)}
                >
                  Reconnect
                </Button>
              )}
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}

// Example campaign creation form addition
export function CampaignTypeSelector({ value, onChange }) {
  const campaignTypes = [
    { value: 'email', label: 'Email Only' },
    { value: 'call', label: 'Phone Call Only' },
    { value: 'email_and_call', label: 'Email + Call' },
    { value: 'linkedin', label: 'LinkedIn Only' },
    { value: 'linkedin_and_email', label: 'LinkedIn + Email' },
    { value: 'linkedin_and_call', label: 'LinkedIn + Call' },
    { value: 'all_channels', label: 'All Channels' }
  ];

  return (
    <div>
      <label className="block text-sm font-medium mb-2">Campaign Type</label>
      <select 
        value={value} 
        onChange={(e) => onChange(e.target.value)}
        className="w-full border rounded px-3 py-2"
      >
        {campaignTypes.map(type => (
          <option key={type.value} value={type.value}>
            {type.label}
          </option>
        ))}
      </select>
    </div>
  );
}

// LinkedIn campaign fields
export function LinkedInCampaignFields({ campaign, onChange }) {
  if (!['linkedin', 'linkedin_and_email', 'linkedin_and_call', 'all_channels'].includes(campaign.type)) {
    return null;
  }

  return (
    <div className="space-y-4 border-t pt-4">
      <h4 className="font-medium">LinkedIn Settings</h4>
      
      <div>
        <label className="block text-sm font-medium mb-2">
          LinkedIn Message Template
        </label>
        <textarea
          value={campaign.linkedin_message_template || ''}
          onChange={(e) => onChange({ ...campaign, linkedin_message_template: e.target.value })}
          className="w-full border rounded px-3 py-2 h-32"
          placeholder="Hi {lead_first_name}, I noticed {lead_company} is..."
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">
          LinkedIn Invitation Template (300 char max)
        </label>
        <textarea
          value={campaign.linkedin_invitation_template || ''}
          onChange={(e) => onChange({ ...campaign, linkedin_invitation_template: e.target.value })}
          className="w-full border rounded px-3 py-2 h-20"
          maxLength={300}
          placeholder="Hi {lead_first_name}, I'd like to connect..."
        />
        <p className="text-sm text-gray-500 mt-1">
          {campaign.linkedin_invitation_template?.length || 0}/300 characters
        </p>
      </div>

      <div>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={campaign.linkedin_inmail_enabled || false}
            onChange={(e) => onChange({ ...campaign, linkedin_inmail_enabled: e.target.checked })}
          />
          <span className="text-sm">Enable InMail (Premium feature)</span>
        </label>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium mb-2">
            Number of LinkedIn Reminders
          </label>
          <input
            type="number"
            min="0"
            max="5"
            value={campaign.linkedin_number_of_reminders || 0}
            onChange={(e) => onChange({ 
              ...campaign, 
              linkedin_number_of_reminders: parseInt(e.target.value) 
            })}
            className="w-full border rounded px-3 py-2"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium mb-2">
            Days Between Reminders
          </label>
          <input
            type="number"
            min="1"
            max="30"
            value={campaign.linkedin_days_between_reminders || 3}
            onChange={(e) => onChange({ 
              ...campaign, 
              linkedin_days_between_reminders: parseInt(e.target.value) 
            })}
            className="w-full border rounded px-3 py-2"
          />
        </div>
      </div>
    </div>
  );
}
