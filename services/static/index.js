function msgstyle(finish){
    if (finish == 0) 
       return  'background-color:#fffffb';

    return  'background-color:#F08080';
}


function loadData() {
    $.ajax({
        url: '/getResult', 
        type: 'GET', 
        data: '',
        error:function (data) {
            alert('请求失败');
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

                proc =  cur *100.0 / (tx+minconf);
                var procstr = (cur-tx) + "/" + minconf;

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
                "<td align='right'>" + arr[j]['fee'] + "</td>" +       
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



function up() {
    document.getElementById('progress').value = 50;
    document.getElementById('progressNumber').style.width = 50 + "%";   
}