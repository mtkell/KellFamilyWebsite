<%@ Control Language="VB" ClassName="Todayls" %>

<script runat="server">

    Protected Sub Page_Load(ByVal sender As Object, ByVal e As System.EventArgs)
        litTodayIs.Text = DateTime.Today.ToLongDateString
    End Sub
</script>
<p>
    Today is:
    <asp:Literal ID="litTodayls" runat="server"></asp:Literal>
</p>

