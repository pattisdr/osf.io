<%inherit file="notify_base.mako" />


<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    Failed to send ${node.type} "${node.title}" (${node.url}) [${node._id}] to SHARE (status: ${resp.status_code}; retries: ${retries})

    <br />
     Error:
    ${resp.text}
  </td>
</tr>
</%def>
