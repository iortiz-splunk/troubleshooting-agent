---
title: "Connect to EC2 Instance"
description: "Connect to your workshop EC2 instance, retrieve your instance name, and optionally set up VS Code remote editing."
weight: 3
navTitle: "Connect to EC2 Instance"
duration: "5 minutes"
---

We've prepared an Ubuntu Linux instance in AWS/EC2 for each attendee:

- Access the **Splunk Show** event by clicking on the link for your region
- Click **Enroll** on the top-right corner
- Then look near the bottom of the page for your EC2 instance details

You should see connection information such as the following:

{{< diagram src="images/ConnectionInformation.png" alt="Splunk Show EC2 connection information with SSH command and password" >}}

Using the IP address (which is part of the **SSH Command**) and **SSH Password** provided as part of the **Connection Information**, connect to your EC2 instance using one of the methods below:

- **Mac OS / Linux** — `ssh splunk@IP address`
- **Windows 10+** — Use the OpenSSH client
- **Earlier versions of Windows** — Use PuTTY

{{< notice title="Note" style="primary" >}}
Answer **yes** when asked if you want to continue connecting.
{{< /notice >}}

{{< diagram src="images/ssh-connection.png" alt="Terminal prompt asking to confirm SSH connection fingerprint" >}}

{{< notice title="VPN Connection" style="green" >}}

If you're working from an office and having trouble connecting, try connecting to your corporate VPN first.

{{< /notice >}}

## Retrieve your Instance Name

Once you've logged into your EC2 instance via SSH, use the following command to get your instance name:

```bash
echo $INSTANCE
```

Make a note of this, as your instance name is unique to you and will be used later in the workshop to find your data in Splunk Observability Cloud.

## Connect Visual Studio Code (Optional)

{{< notice title="Tip" style="tip" >}}
We'll be editing several files throughout the workshop. The workshop instructions include tips for doing this using a `vi` editor, and workshop participants can use the `nano` editor as well.
{{< /notice >}}

If you prefer a full-fledged IDE, you can connect Visual Studio Code running on your laptop to edit remote files on the EC2 instance.

The high-level steps to do this are as follows:

1. Download and install VS Code on your machine using [this link](https://code.visualstudio.com/download).
2. In VS Code, navigate to **Settings** and then **Extensions**.
3. Search for the **Remote – SSH extension** (by Microsoft) and install it.

{{< diagram src="images/InstallRemoteSSH.png" alt="VS Code Extensions view showing Remote SSH extension" >}}

4. Press **F1** (or Ctrl+Shift+P on Windows / Cmd+Shift+P on Mac OS).
5. Run **Remote-SSH: Connect to Host**.
6. Copy your SSH command from Splunk Show: `ssh -p 2222 splunk@EC2_PUBLIC_IP`.
7. Choose the default SSH config file when prompted.
8. Press **F1** (or Ctrl+Shift+P on Windows / Cmd+Shift+P on Mac OS) again.
9. Run **Remote-SSH: Connect to Host**.
10. Select the host you just added. VS Code will open a new window and start the connection.
11. A prompt will appear at the top of VS Code asking for the **SSH password**. Copy the password from Splunk Show and enter it here.
12. Click **Open Folder** then input `/home/splunk` as the folder name:

{{< diagram src="images/OpenRemoteFolder.png" alt="VS Code Open Folder dialog with /home/splunk path" >}}

You can now edit files remotely with VS Code!
