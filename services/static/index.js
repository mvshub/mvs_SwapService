function msgstyle(finish){
    if (finish == 0) 
       return  'background-color:#fffffb';

    return  'background-color:#F08080';
}


function loadData() {
    var pageIndex = $('#page_index').attr('pi');
    $.ajax({
        url: '/getResult/'+pageIndex, 
        type: 'GET', 
        data: '',
        error:function (data) {
        },
        success:function (data) {
            $("#result").html("");
            var arr = JSON.parse(data);
            var str='';    
            for(j = 0; j < arr.length; j++) {
                var minconf = arr[j]['minconf'];
                var cur = 0, tx = 0, proc =0; 
                if (arr[j]['tx_height'] != null )
                    tx = arr[j]['tx_height'];

                if (arr[j]['confirm_height'] != null)
                    cur = arr[j]['confirm_height'];
                
                var procstr= "0/" + minconf;
                if(cur >= tx){
                    proc = (cur - tx)*100.0 / (minconf);
                    procstr = Math.min(cur-tx, minconf) + "/" + minconf;
                }
            

                str += "<tr>" +
                "<td align='center'>" + arr[j]['swap_id'] + "</td>" + 
                "<td align='right'>" + arr[j]['coin'] + "</td>" + 
                "<td align='right'>" +
                "<a href= '/token/" + arr[j]['token'] + "'>" +  arr[j]['token'] + "</a>" + 
                "</td>" +
                "<td align='right'>" +
                "<a href= '/address/" + arr[j]['from'] + "'>" + arr[j]['from'] + "</a>" + 
                "</td>" +
                "<td align='right'>" +
                "<a href= '/address/" + arr[j]['to'] + "'>" + arr[j]['to'] + "</a>" + 
                "</td>" +
                "<td align='right'>" + arr[j]['amount'] + "</td>" + 
                // "<td align='right'>" + arr[j]['fee'] + "</td>" +       
                "<td align='center' >"+
                "<div> <span>" + procstr + "<span>"+ "<progress value='"+ Math.ceil(proc) + "' max='100'>" + "</progress>" + 
                "</td>" +
                "<td align='center' style='" + msgstyle(arr[j]['finish']) + "'>" + arr[j]['message'] + "</td>"+
                "<td align='right'>" +
                "<a href= '/date/" + arr[j]['date'] + "'>" +  arr[j]['date'] + "</a>" + 
                "</td>" +
                "<td align='center'>" + arr[j]['time'] + "</td>" + 
                "<td align='center'>" +
                "<a href= '/tx/" + arr[j]['tx_from'] + "'>" + "More" + "</a>" + 
                "</td>" +
                "</tr>";
            } 
            $("#result").append(str);
        }
    });
}

function loadBan(){
    var pageIndex = $('#page_index').attr('pi');
    var date = $('#dateid').attr('d');
    $.ajax({
        url: '/getBan/'+date+'/'+pageIndex, 
        type: 'GET', 
        data: '',
        error:function (data) {
        },
        success:function (data) {
            $("#result").html("");
            var arr = JSON.parse(data);
            var str='';    
            for(j = 0; j < arr.length; j++) {
                str += "<tr>" +
                "<td align='center'>" + arr[j]['swap_id'] + "</td>" + 
                "<td align='right'>" + arr[j]['coin'] + "</td>" + 
                "<td align='right'>" +
                "<a href= '/token/" + arr[j]['token'] + "'>" +  arr[j]['token'] + "</a>" + 
                "</td>" +
                "<td align='right'>" +
                "<a href= '/address/" + arr[j]['from'] + "'>" + arr[j]['from'] + "</a>" + 
                "</td>" +
                "<td align='right'>" +
                "<a href= '/address/" + arr[j]['to'] + "'>" + arr[j]['to'] + "</a>" + 
                "</td>" +
                "<td align='right'>" + arr[j]['amount'] + "</td>" + 
                "<td align='center'>" + arr[j]['message'] + "</td>"+
                "<td align='center'>" + arr[j]['time'] + "</td>" + 
                "<td align='center'>" + 
                "<a href='javascript:void(0);' onclick='javascript:retry_swap(" +
                arr[j]['swap_id']  + ");return false;'>" + 'Retry' + "</a>" +
                "</td>" + 
                "<td align='center'>" + 
                "<a href='" + arr[j]['scan']  + "' target='_blank'>" + 'Scan' + "</a>" +
                "</td>" + 
                "</tr>";
            } 
            $("#result").append(str);
        }
    });
}

function retry_swap(swap_id)
{
    var d = {'swap_id':swap_id}
    $.ajax({
        url: '/retry', 
        type: 'POST', 
        data: d,
        error:function (data) {
            alert('post retry request failed')
        },
        success:function (data) {
            var arr = JSON.parse(data);
            if (arr['code'] != 0){
                alert('retry failed:' + arr['result'])
            }
            else{
                alert('retry success:' + arr['result'])
            }

        }
    });
}

function up() {
    document.getElementById('progress').value = 50;
    document.getElementById('progressNumber').style.width = 50 + "%";   
}
