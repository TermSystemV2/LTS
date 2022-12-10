<template>
    <div ref="studentInfoBarRef" class="chart">
        <!-- <p>{{ fatherDataName }}</p> -->
    </div>
</template>

<script setup lang="ts">
import { onMounted, ref, defineProps } from 'vue';
import * as echarts from 'echarts';
import 'echarts/theme/macarons.js';
import { fetchExcellentBarData } from '../api/index';

const props = defineProps({
    chartData: Object,
});
const studentInfoBarRef = ref<HTMLDivElement>()
onMounted(() => {
    console.log('props.chartData:',props.chartData);
    let data = props.chartData;
    let totalWeightedScoreTerm = data?.totalWeightedScoreTerm;
    let failedSubjectNumsTerm = data?.failedSubjectNumsTerm;
    
    // 基于准备好的dom，初始化echarts实例
    var myChart = echarts.init(studentInfoBarRef.value as HTMLDivElement, 'macarons');
    var option = {
        tooltip: {
            trigger: 'axis',
            axisPointer: {
                type: 'cross',
                crossStyle: {
                    color: '#999'
                }
            }
        },
        toolbox: {
            feature: {
                dataView: { show: true, readOnly: false },
                magicType: { show: true, type: ['bar', 'bar'] },
                restore: { show: true },
                saveAsImage: { show: true }
            }
        },
        legend: {
            data: ['学年加权分', '学年挂科数量']
        },
        xAxis: [
            {
                type: 'category',
                data: ['第一学年','第二学年','第三学年','第四学年'],
                axisPointer: {
                    type: 'shadow'
                }
            }
        ],
        yAxis: [
            {
                type: 'value',
                name: '分数',
                min: 0,
                max: 100,
                interval: 10,
                axisLabel: {
                    formatter: '{value} 分'
                }
            },
            {
                type: 'value',
                name: '个数',
                min: 0,
                max: 35,
                interval: 5,
                axisLabel: {
                    formatter: '{value} 个'
                }
            }
        ],
        series: [
            {
                name: '学年加权分',
                type: 'bar',
                tooltip: {
                    valueFormatter: function (value: string) {
                        return value + ' 分';
                    }
                },
                data: totalWeightedScoreTerm
            },
            {
                name: '学年挂科数量',
                type: 'bar',
                yAxisIndex: 1,
                tooltip: {
                    valueFormatter: function (value: string) {
                        return value + ' 个';
                    }
                },
                data: failedSubjectNumsTerm
            }
        ]
    };
    // 绘制图表
    myChart.setOption(option);
    window.addEventListener('resize', () => {
        myChart.resize()
    })

})
</script>
<style scoped>
.chart {
    width: 800px;
    height: 500px;
}
</style>